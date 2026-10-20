#!/usr/bin/env python3
"""Learner HTTP review through an authorized loopback port-forward; no pod exec or Secret access."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class ReviewError(ValueError):
    pass


class ApiError(ReviewError):
    def __init__(self,status,detail):
        self.status=status
        self.detail=detail
        super().__init__('Live API returned HTTP '+str(status))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def finite(value):
    if isinstance(value,float) and not math.isfinite(value):
        raise ReviewError('Non-finite artifact is not reviewable')
    if isinstance(value,dict):
        for item in value.values():finite(item)
    elif isinstance(value,list):
        for item in value:finite(item)


def load(path):
    value=json.loads(Path(path).read_text())
    finite(value)
    return value


class Client:
    def __init__(self,base_url,namespace,workdir,service='checkout-api'):
        parsed=urlsplit(base_url)
        if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
            raise ReviewError('Use only an HTTP loopback URL for the authorized port-forward')
        if not parsed.port:
            raise ReviewError('Specify the local port-forward port')
        for value in (namespace,service):
            if len(value)>63 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?',value):
                raise ReviewError('Namespace and service must be Kubernetes DNS labels')
        self.base=base_url.rstrip('/')
        self.namespace=namespace
        self.service=service
        self.workdir=Path(workdir)
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def api(self,path,payload=None):
        body=None if payload is None else json.dumps(payload,allow_nan=False).encode()
        request=Request(self.base+path,data=body,headers={'Content-Type':'application/json'})
        try:
            with self.opener.open(request,timeout=180) as response:
                value=json.load(response)
                headers={key.lower():value for key,value in response.headers.items()}
            finite(value)
            if not isinstance(value,dict):
                raise ReviewError('Expected an object from the live API')
            return value,headers
        except HTTPError as error:
            detail='Request did not pass; inspect the status and missing prerequisite'
            try:
                detail=json.load(error).get('detail',detail)
            except (ValueError,AttributeError):
                pass
            raise ApiError(error.code,detail) from error
        except (URLError,TimeoutError,OSError) as error:
            raise ReviewError('Loopback API unavailable; confirm the authorized port-forward and application readiness') from error

    def scoped(self,artifact,namespace=True):
        finite(artifact)
        if not isinstance(artifact,dict) or isinstance(artifact.get('schema_version'),bool) or artifact.get('schema_version')!=1 or artifact.get('service')!=self.service:
            raise ReviewError('Artifact schema/service differs from this review')
        if namespace and artifact.get('namespace')!=self.namespace:
            raise ReviewError('Artifact belongs to another namespace')
        coverage=artifact.get('coverage_ratio',artifact.get('provenance',{}).get('coverage_ratio'))
        if isinstance(coverage,bool) or not isinstance(coverage,(int,float)) or not math.isfinite(coverage) or coverage<.8 or coverage>1:
            raise ReviewError('At least 0.8 finite measured coverage is required')
        return coverage

    def write(self,name,value,exclusive=False):
        self.workdir.mkdir(parents=True,exist_ok=True,mode=0o700)
        path=self.workdir/name
        if path.is_symlink():
            raise ReviewError('Refuse a redirected local receipt')
        with path.open('x' if exclusive else 'w') as handle:
            json.dump(value,handle,sort_keys=True,indent=2,allow_nan=False)
            handle.write('\n')

    def check(self):
        health,_=self.api('/health')
        if health.get('status')!='ok':
            raise ReviewError('Application health check did not pass')
        evidence,headers=self.api('/api/v1/evidence',{'service':self.service,'namespace':self.namespace,'mode':'live'})
        coverage=self.scoped(evidence)
        sha=digest(evidence)
        if headers.get('x-sloscope-mode')!='live' or headers.get('x-sloscope-input-sha256')!=sha:
            raise ReviewError('Evidence response is not live and bound to its canonical artifact digest')
        series=evidence.get('series',{})
        requests=series.get('request_total',{}).get('total',0)
        histogram=series.get('latency_histogram',{}).get('total_count',0)
        if any(isinstance(value,bool) or not isinstance(value,(int,float)) or value<=0 for value in (requests,histogram)):
            raise ReviewError('Evidence lacks measured request/histogram counts')
        self.write('evidence.json',evidence)
        result={'status':'live_evidence_checked','service':self.service,'namespace':self.namespace,
                'coverage_ratio':coverage,'lookback':evidence.get('lookback_window'),'request_count':requests,
                'histogram_count':histogram,'input_sha256':sha,'model_called':False}
        self.write('evidence-receipt.json',result)
        return result

    def collect(self):
        result,_=self.api('/api/v2/collect',{'service':self.service,'namespace':self.namespace})
        if result.get('status')!='ok' or result.get('service')!=self.service or result.get('reference') not in ('initialized','preserved'):
            raise ReviewError('Collection did not return the expected service/reference status')
        return result

    def baseline(self):
        baseline,_=self.api('/api/v2/services/'+self.service+'/baseline')
        self.scoped(baseline)
        return baseline

    def reference(self):
        if (self.workdir/'baseline-reference.json').exists() or (self.workdir/'reference-receipt.json').exists():
            raise ReviewError('A local reference already exists; preserve it and use compare or a new workdir')
        self.check()
        collected=self.collect()
        baseline=self.baseline()
        sha=digest(baseline)
        receipt={'status':'reference_recorded','service':self.service,'namespace':self.namespace,'baseline_sha256':sha,
                 'remote_reference':collected['reference'],'approval':'human_review_required'}
        self.write('baseline-reference.json',baseline,exclusive=True)
        self.write('reference-receipt.json',receipt,exclusive=True)
        return receipt

    def reference_files(self):
        baseline=load(self.workdir/'baseline-reference.json')
        receipt=load(self.workdir/'reference-receipt.json')
        self.scoped(baseline)
        sha=digest(baseline)
        if receipt.get('baseline_sha256')!=sha or receipt.get('namespace')!=self.namespace or receipt.get('service')!=self.service:
            raise ReviewError('Local reference or receipt changed; do not promote it silently')
        return baseline,sha

    def compare(self):
        baseline,sha=self.reference_files()
        self.check()
        collected=self.collect()
        if collected['reference']!='preserved' or collected.get('drift_computed') is not True:
            raise ReviewError('Server did not preserve a reference and compute drift; local reference is unchanged')
        if digest(self.baseline())!=sha:
            raise ReviewError('Remote baseline differs from the preserved local reference')
        signal,_=self.api('/api/v2/services/'+self.service+'/drift')
        coverage=self.scoped(signal,namespace=False)
        receipt={'status':'reference_preserved_and_drift_recorded','service':self.service,'namespace':self.namespace,
                 'baseline_sha256':sha,'drift_sha256':digest(signal),'coverage_ratio':coverage,
                 'breached_indicators':signal.get('all_breached_indicators',[]),'approval':'human_review_required'}
        self.write('drift-signal.json',signal)
        self.write('comparison-receipt.json',receipt)
        # Read the preserved file again: writing comparison artifacts must never replace it.
        if digest(load(self.workdir/'baseline-reference.json'))!=sha:
            raise ReviewError('Local reference changed during comparison')
        return receipt

    def classify(self):
        baseline,reference_sha=self.reference_files()
        signal=load(self.workdir/'drift-signal.json')
        self.scoped(signal,namespace=False)
        comparison=load(self.workdir/'comparison-receipt.json')
        sha=digest(signal)
        if comparison.get('drift_sha256')!=sha or comparison.get('baseline_sha256')!=reference_sha or comparison.get('namespace')!=self.namespace or comparison.get('service')!=self.service:
            raise ReviewError('Local comparison artifacts or receipt changed')
        if digest(self.baseline())!=reference_sha:
            raise ReviewError('Remote baseline no longer matches this review reference')
        report,headers=self.api('/api/v1/drift/classify',{'drift_signal':signal,'mode':'live'})
        constraint=report.get('evidence_constraint',{})
        if headers.get('x-sloscope-mode')!='live' or headers.get('x-sloscope-input-sha256')!=sha or constraint.get('input_sha256')!=sha:
            raise ReviewError('Live classification is not bound to the submitted signal in both header and constraint')
        if report.get('service')!=self.service or constraint.get('policy')!='measured-drift-v1' or constraint.get('prose_status')!='advisory_not_verified_causality':
            raise ReviewError('Report omitted the expected service, evidence policy or advisory boundary')
        if not isinstance(report.get('classification'),str) or not report['classification'].strip() or not isinstance(report.get('recommendations'),list) or not report['recommendations']:
            raise ReviewError('Live classification result is incomplete')
        receipt={'status':'live_report_validated','service':self.service,'namespace':self.namespace,'input_sha256':sha,
                 'classification':report['classification'],'policy':constraint['policy'],
                 'prose_status':constraint['prose_status'],'human_review_required':True}
        self.write('classification-report.json',report)
        self.write('classification-receipt.json',receipt)
        return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['check','reference','compare','classify'])
    parser.add_argument('--namespace',required=True)
    parser.add_argument('--service',default='checkout-api')
    parser.add_argument('--base-url',default='http://127.0.0.1:18080')
    parser.add_argument('--workdir',type=Path,default=Path(__file__).resolve().parents[1]/'.lab/live-learner')
    args=parser.parse_args(argv)
    try:
        result=getattr(Client(args.base_url,args.namespace,args.workdir,args.service),args.command)()
        print(json.dumps(result,sort_keys=True))
        return 0
    except ApiError as error:
        print(json.dumps({'status':'abstained' if error.status==422 else 'failed','http_status':error.status,'reason':error.detail}),file=sys.stderr)
        return 2 if error.status==422 else 1
    except (ReviewError,OSError,ValueError,TypeError,KeyError) as error:
        print(json.dumps({'status':'failed','reason':str(error)}),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
