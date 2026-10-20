"""Explicit real model interpretation of the persisted controlled-workload drift signal."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError

APP_ROOT=Path(os.environ.get("SLOSCOPE_APP_ROOT","/app"))
sys.path.insert(0,str(APP_ROOT))
sys.path.insert(0,str(APP_ROOT/"analysis"))

from backend.store import ArtifactStore
from evidence_constraints import input_digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace',required=True)
    args=parser.parse_args()
    if os.environ.get('SLOSCOPE_REQUIRE_MODEL','true')!='true':
        raise ValueError('Measurement-only profile: provision the dedicated model Secret and redeploy require_model=true before interpretation')
    store=ArtifactStore()
    baseline=store.load('checkout-api','baseline')
    signal=store.load('checkout-api','drift-signal')
    if not baseline or baseline.get('namespace')!=args.namespace or not signal:
        raise ValueError('Collect a reference and a second comparable window in this namespace first')
    req=Request('http://127.0.0.1:8080/api/v1/drift/classify',data=json.dumps({'drift_signal':signal,'mode':'live'}).encode(),
                headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=120) as response:
        report=json.load(response)
        headers={key.lower():value for key,value in response.headers.items()}
    constraint=report.get('evidence_constraint',{})
    if headers.get('x-sloscope-mode')!='live' or constraint.get('input_sha256')!=input_digest(signal):
        raise ValueError('Response is not bound to the submitted live signal')
    store.save('checkout-api','drift-report',report)
    print(json.dumps({'status':'live_report_validated','service':'checkout-api','namespace':args.namespace,
                     'input_sha256':constraint['input_sha256'],'policy':constraint.get('policy'),
                     'prose_status':constraint.get('prose_status'),'approval':'human_review_required'},sort_keys=True))

if __name__=='__main__':
    try:
        main()
    except HTTPError as error:
        detail=None
        if error.code==422:
            try:
                detail=json.load(error).get('detail')
            except (ValueError,AttributeError):
                pass
        print(json.dumps({'status':'abstained' if error.code==422 else 'failed','http_status':error.code,
                          'reason':detail or 'Live classification did not pass; inspect server logs privately'}),file=sys.stderr)
        raise SystemExit(2)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'failed','reason':str(error)}),file=sys.stderr)
        raise SystemExit(1)
