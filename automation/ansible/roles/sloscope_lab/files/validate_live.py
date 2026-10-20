"""Readiness/telemetry checks inside the engine pod; no deployment or model call by default."""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError


def request(url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(url,data=data,headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=120) as response:
        return json.load(response),dict(response.headers)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace',required=True)
    parser.add_argument('--model',action='store_true',help='Explicitly request real model proposal validation')
    parser.add_argument('--telemetry-only',action='store_true',help='Validate controlled scrape/counters before engine/model provisioning')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?',args.namespace):
        raise ValueError('Invalid namespace')
    if args.model and (args.telemetry_only or os.environ.get('SLOSCOPE_REQUIRE_MODEL','true')!='true'):
        raise ValueError('Model validation requires the configured-model profile')
    endpoint=os.environ.get('PROM_URL','http://sloscope-prometheus:9090')
    if not args.telemetry_only:
        health,_=request('http://127.0.0.1:8080/health')
    query='up{job="checkout-lab"}'
    up,_=request(endpoint+'/api/v1/query?'+urlencode({'query':query}))
    values=[float(item['value'][1]) for item in up['data']['result']]
    if not values or not all(value==1 for value in values):
        raise ValueError('Controlled checkout scrape is not healthy')
    if args.telemetry_only:
        query='sum(http_requests_total{service="checkout-api",namespace="'+args.namespace+'"})'
        measured,_=request(endpoint+'/api/v1/query?'+urlencode({'query':query}))
        values=[float(item['value'][1]) for item in measured['data']['result']]
        if not values or not all(math.isfinite(value) and value>0 for value in values):
            raise ValueError('No measured controlled checkout requests yet')
        print(json.dumps({'status':'validated','mode':'live_controlled_telemetry_only','request_counter':sum(values),
                          'namespace':args.namespace,'service':'checkout-api','model_validation':'not_requested'}))
        return
    evidence,evidence_headers=request('http://127.0.0.1:8080/api/v1/evidence',{'service':'checkout-api','namespace':args.namespace,'mode':'live'})
    evidence_headers={key.lower():value for key,value in evidence_headers.items()}
    evidence_digest=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if evidence_headers.get('x-sloscope-mode')!='live' or evidence_headers.get('x-sloscope-input-sha256')!=evidence_digest:
        raise ValueError('Evidence response is not labeled live and bound to its artifact digest')
    if evidence.get('service')!='checkout-api' or evidence.get('namespace')!=args.namespace:
        raise ValueError('Collected evidence identity mismatch')
    coverage=evidence.get('coverage_ratio',0)
    if not math.isfinite(coverage) or coverage<.8:
        raise ValueError('Insufficient live coverage; allow the declared lookback to warm up, then retry')
    series=evidence['series']
    if series['request_total']['total']<=0 or series['latency_histogram']['total_count']<=0:
        raise ValueError('Live evidence does not contain measured request/histogram counts')
    baseline,_=request('http://127.0.0.1:8080/api/v1/baseline',{'evidence':evidence})
    result={'status':'validated','mode':'live_controlled_workload','namespace':args.namespace,'service':'checkout-api',
            'lookback':evidence['lookback_window'],'coverage_ratio':coverage,'request_count':series['request_total']['total'],
            'error_count':series['error_total']['total'],'histogram_count':series['latency_histogram']['total_count'],
            'model_validation':'not_requested','approval':'human_review_required'}
    if args.model:
        proposal,headers=request('http://127.0.0.1:8080/api/v1/propose',{'baseline':baseline,'mode':'live'})
        # Success must be an actual live response, not a recording or empty payload.
        normalized={k.lower():v for k,v in headers.items()}
        baseline_digest=hashlib.sha256(json.dumps(baseline,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if normalized.get('x-sloscope-mode')!='live' or normalized.get('x-sloscope-input-sha256')!=baseline_digest or not proposal.get('slos'):
            raise ValueError('Model response was not a nonempty live proposal bound to this baseline')
        if not all(slo.get('requires_review') is True for slo in proposal['slos']):
            raise ValueError('Model proposal omitted the human-review boundary')
        result['model_validation']='live_proposal_validated'
        result['model_input_sha256']=normalized.get('x-sloscope-input-sha256')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':
    try:
        main()
    except HTTPError as error:
        # Avoid dumping model response bodies or configured credential-bearing endpoints.
        print(json.dumps({'status':'failed','http_status':error.code,'reason':'Live endpoint rejected or failed; inspect server logs privately'}),file=sys.stderr)
        raise SystemExit(1)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'failed','reason':str(error)}),file=sys.stderr)
        raise SystemExit(1)
