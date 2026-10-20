#!/usr/bin/env python3
"""Portable learner exercises using the pinned SLOscope engine; no model or cluster calls."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is not supported for learner verification")

LAB = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('SLOSCOPE_SOURCE', LAB / '.lab' / 'engine')).resolve()
sys.path.insert(0, str(SOURCE / 'analysis'))
sys.path.insert(0, str(SOURCE / 'backend'))

def load(path):
    return json.loads(Path(path).read_text())

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_source():
    lock = load(LAB / 'engine.lock.json')
    actual = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != lock['commit']:
        raise ValueError('Engine source differs from engine.lock.json; rerun setup after preserving changes')
    dirty = subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip()
    if dirty:
        raise ValueError('Engine source contains local changes; acceptance requires the clean pinned source')


def run(args):
    verify_source()
    from baseline import compute_baseline
    from deviation import compute_drift_signal
    from evidence_constraints import classification_constraints, EvidenceConstraintError
    from schemas.validate import validate
    out = Path(args.workdir).resolve()
    if args.command == 'prepare':
        if (out/'evidence.json').exists():
            raise ValueError('Workspace already prepared; choose a new --workdir to preserve your work')
        evidence = load(SOURCE/'testdata/evidence_checkout_api.json')
        # Public synthetic fixture: generic endpoint identifies it as a teaching artifact.
        evidence['provenance']['prometheus_endpoint'] = 'https://metrics.example.com'
        dump(out/'evidence.json', evidence)
        changed = copy.deepcopy(evidence)
        changed['series']['error_total']['total'] = 2300
        changed['collected_at'] = '2026-07-06T14:00:00Z'
        # This is an edited scenario, not a newly collected real telemetry window.
        dump(out/'changed-evidence.json', changed)
        dump(out/'lab-provenance.json', {'mode':'synthetic', 'source':'testdata/evidence_checkout_api.json',
             'change':'error_total.total deliberately changed from 230 to 2300; collected_at set to 2026-07-06T14:00:00Z; other data unchanged',
             'source_sha256':sha(SOURCE/'testdata/evidence_checkout_api.json')})
        print('Prepared SYNTHETIC checkout-api evidence: 100000 requests, 230 errors; scenario: 2300 errors')
    elif args.command == 'baseline':
        if (out/'baseline.json').exists():
            raise ValueError('Reference already exists; baseline command refuses to replace it')
        evidence = load(out/'evidence.json')
        dump(out/'baseline.json', compute_baseline(evidence))
        (out/'reference.sha256').write_text(sha(out/'baseline.json')+'\n')
        print('Reference frozen; error ratio = 0.0023; p99 = 5000 ms')
    elif args.command == 'drift':
        before = sha(out/'baseline.json')
        baseline = load(out/'baseline.json')
        changed = load(out/'changed-evidence.json')
        dump(out/'current-baseline.json', compute_baseline(changed))
        signal = compute_drift_signal({'baseline':baseline, 'live_evidence':changed})
        dump(out/'drift-signal.json', signal)
        assert before == sha(out/'baseline.json') == (out/'reference.sha256').read_text().strip()
        print('Reference preserved; breached indicators: '+', '.join(sorted(signal['all_breached_indicators'])))
    elif args.command == 'review':
        signal = load(args.input or out/'drift-signal.json')
        try:
            constraint = classification_constraints(signal)
        except EvidenceConstraintError as exc:
            print(json.dumps({'status':'abstained','reason':str(exc)}))
            return 2
        print(json.dumps({'status':'admissible','evidence_constraint':constraint}, indent=2))
    elif args.command == 'low-coverage':
        signal = load(out/'drift-signal.json')
        signal['provenance']['coverage_ratio'] = .79
        dump(out/'low-coverage-signal.json', signal)
        print('Created SYNTHETIC low-coverage challenge: 0.79')
    elif args.command == 'conflict':
        signal = load(out/'drift-signal.json')
        signal['all_breached_indicators'] = []
        dump(out/'conflicting-signal.json', signal)
        print('Created SYNTHETIC conflict: breach list no longer matches measured indicators')
    elif args.command == 'export':
        # Recorded proposal is deliberately separate from measured fixture evidence.
        # We test the export boundary, not approval of its business targets.
        from fastapi.testclient import TestClient
        import server
        proposal = load(SOURCE/'analysis/evals/recorded/web_api_baseline_response.json')
        evidence = load(out/'evidence.json')
        if args.bucket_ms is not None:
            for slo in proposal['slos']:
                if slo['sli_type']=='latency':
                    slo['sla_target']=args.bucket_ms
        validate(proposal, 'proposal')
        with TestClient(server.app) as client:
            response=client.post('/api/v1/render',json={'proposal':proposal,'service':'checkout-api','namespace':'payments','evidence':evidence})
        if response.status_code!=200:
            print(json.dumps({'status':'rejected','http_status':response.status_code,'detail':response.json()['detail']}))
            return 2
        dump(out/'export-preview.json',response.json())
        dump(out/'export-receipt.json', {'status':'preview_only_human_review_required',
             'source_commit':load(LAB/'engine.lock.json')['commit'], 'evidence_sha256':sha(out/'evidence.json'),
             'preview_sha256':sha(out/'export-preview.json'), 'service':'checkout-api','namespace':'payments',
             'latency_bucket_ms':args.bucket_ms, 'manual_recorded_proposal_edit':True})
        print('Rendered preview with observed histogram bucket; targets still require human review')
    elif args.command == 'boundary':
        from fastapi.testclient import TestClient
        import server
        # No credentials are needed. Absence is deliberate for this negative test.
        os.environ.pop('LLM_BASE_URL',None)
        os.environ.pop('LLM_API_KEY',None)
        with TestClient(server.app) as client:
            live=client.post('/api/v1/propose',json={'baseline':load(out/'baseline.json')})
            fixture=client.post('/api/v1/propose',json={'baseline':load(out/'baseline.json'),'mode':'fixture'})
        assert live.status_code==503,live.text
        assert fixture.status_code==200 and fixture.headers['X-SLOscope-Mode']=='fixture'
        print('PASS: default live mode returns 503 without a model; explicit fixture returns labeled demonstration')
    elif args.command == 'check':
        reference = load(out/'baseline.json')
        current = load(out/'current-baseline.json')
        assert sha(out/'baseline.json') == (out/'reference.sha256').read_text().strip(), 'Reference changed'
        assert reference['indicators']['error_rate']['ratio']==.0023
        assert current['indicators']['error_rate']['ratio']==.023
        constraint=classification_constraints(load(out/'drift-signal.json'))
        assert {'error_rate_ratio','availability_ratio'} <= set(constraint['breached_indicators'])
        for name in ('low-coverage-signal.json','conflicting-signal.json'):
            try:
                classification_constraints(load(out/name))
            except EvidenceConstraintError:
                pass
            else:
                raise AssertionError(name+' incorrectly admitted')
        preview=load(out/'export-preview.json')
        receipt=load(out/'export-receipt.json')
        assert receipt['status']=='preview_only_human_review_required'
        assert receipt['source_commit']==load(LAB/'engine.lock.json')['commit']
        assert receipt['preview_sha256']==sha(out/'export-preview.json'), 'Preview changed'
        assert receipt['evidence_sha256']==sha(out/'evidence.json'), 'Export evidence changed'
        assert receipt['service']=='checkout-api' and receipt['namespace']=='payments'
        assert receipt['manual_recorded_proposal_edit'] is True and receipt['latency_bucket_ms']==1000
        assert 'service: checkout-api' in preview['openslo_yaml']
        assert 'service="checkout-api",namespace="payments",le="1.0"' in preview['prom_rules']
        assert 'SLORequestLatencyP99BurnRateCritical' in preview['prom_rules']
        print('PASS: preserved reference, measured drift, 2 abstentions, and reviewed-bucket export preview')
    return 0

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','baseline','drift','review','low-coverage','conflict','export','boundary','check'])
    parser.add_argument('--workdir',default=str(LAB/'.lab'/'learner'))
    parser.add_argument('--input',type=Path)
    parser.add_argument('--bucket-ms',type=float)
    try:
        return run(parser.parse_args())
    except (ValueError,AssertionError,OSError,ImportError,subprocess.CalledProcessError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
