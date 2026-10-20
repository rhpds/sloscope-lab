"""Protocol regressions over a real loopback socket; server data is an explicit synthetic test double."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlsplit

import pytest

ROOT=Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@pytest.fixture
def api():
    evidence={'schema_version':1,'service':'checkout-api','namespace':'lab-user','coverage_ratio':.9,'lookback_window':'5m',
              'series':{'request_total':{'total':100},'latency_histogram':{'total_count':100}}}
    baseline={'schema_version':1,'service':'checkout-api','namespace':'lab-user','provenance':{'coverage_ratio':.9},
              'indicators':{'error_rate':{'ratio':.02}}}
    signal={'schema_version':1,'service':'checkout-api','provenance':{'coverage_ratio':.9},'all_breached_indicators':['error_rate_ratio']}
    state={'evidence':evidence,'baseline':baseline,'signal':signal,'collections':0,'bad_evidence_digest':False,
           'bad_report_digest':False,'reject_model':False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,value,headers=None):
            data=json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            for key,value in (headers or {}).items():self.send_header(key,value)
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/health':return self.send(200,{'status':'ok'})
            if path.endswith('/baseline'):return self.send(200,state['baseline'])
            if path.endswith('/drift'):return self.send(200,state['signal'])
            return self.send(404,{'detail':'unknown path'})
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if self.path=='/api/v1/evidence':
                assert payload['mode']=='live'
                sha='0'*64 if state['bad_evidence_digest'] else digest(state['evidence'])
                return self.send(200,state['evidence'],{'X-SLOscope-Mode':'live','X-SLOscope-Input-SHA256':sha})
            if self.path=='/api/v2/collect':
                state['collections']+=1
                return self.send(200,{'status':'ok','service':'checkout-api','reference':'preserved','drift_computed':True})
            if self.path=='/api/v1/drift/classify':
                assert payload['mode']=='live'
                if state['reject_model']:
                    return self.send(422,{'detail':{'status':'abstained','reason':'Synthetic protocol rejection'}})
                sha=digest(payload['drift_signal'])
                report={'schema_version':1,'service':'checkout-api','classification':'error_rate_elevation',
                    'recommendations':[{'action':'Review evidence before changing any target'}],
                    'evidence_constraint':{'input_sha256':sha,'policy':'measured-drift-v1','prose_status':'advisory_not_verified_causality'}}
                header_sha='0'*64 if state['bad_report_digest'] else sha
                return self.send(200,report,{'X-SLOscope-Mode':'live','X-SLOscope-Input-SHA256':header_sha})
            return self.send(404,{'detail':'unknown path'})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        yield 'http://127.0.0.1:'+str(server.server_port),state
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


def run(command,url,directory):
    return subprocess.run([sys.executable,str(ROOT/'scripts/live-client.py'),command,'--base-url',url,
                           '--namespace','lab-user','--workdir',str(directory)],capture_output=True,text=True)


def test_evidence_digest_mismatch_is_not_accepted(api,tmp_path):
    url,state=api;state['bad_evidence_digest']=True
    result=run('check',url,tmp_path)
    assert result.returncode!=0
    assert 'canonical artifact digest' in result.stderr
    assert not (tmp_path/'evidence-receipt.json').exists()


def test_reference_preserved_and_remote_change_rejected(api,tmp_path):
    url,state=api
    assert run('reference',url,tmp_path).returncode==0
    before=(tmp_path/'baseline-reference.json').read_bytes()
    assert run('compare',url,tmp_path).returncode==0
    assert (tmp_path/'baseline-reference.json').read_bytes()==before
    assert json.loads((tmp_path/'comparison-receipt.json').read_text())['baseline_sha256']==digest(state['baseline'])
    state['baseline']['indicators']['error_rate']['ratio']=.5
    result=run('compare',url,tmp_path)
    assert result.returncode!=0 and 'Remote baseline differs' in result.stderr
    assert (tmp_path/'baseline-reference.json').read_bytes()==before


def test_local_reference_tamper_stops_before_collection(api,tmp_path):
    url,state=api
    assert run('reference',url,tmp_path).returncode==0
    calls=state['collections']
    path=tmp_path/'baseline-reference.json';changed=json.loads(path.read_text());changed['service']='other';path.write_text(json.dumps(changed))
    result=run('compare',url,tmp_path)
    assert result.returncode!=0 and state['collections']==calls


def test_model_rejection_and_digest_mismatch_remain_nonzero(api,tmp_path):
    url,state=api
    assert run('reference',url,tmp_path).returncode==0
    assert run('compare',url,tmp_path).returncode==0
    state['reject_model']=True
    rejected=run('classify',url,tmp_path)
    assert rejected.returncode==2 and 'abstained' in rejected.stderr
    assert not (tmp_path/'classification-report.json').exists()
    state['reject_model']=False;state['bad_report_digest']=True
    bad=run('classify',url,tmp_path)
    assert bad.returncode!=0 and 'both header and constraint' in bad.stderr
    assert not (tmp_path/'classification-report.json').exists()
    state['bad_report_digest']=False
    accepted=run('classify',url,tmp_path)
    assert accepted.returncode==0,accepted.stderr
    assert json.loads(accepted.stdout)['human_review_required'] is True
    assert (tmp_path/'classification-report.json').exists()


def test_comparison_archives_accepted_report_and_rejection_leaves_no_current_report(api,tmp_path):
    url,state=api
    assert run('reference',url,tmp_path).returncode==0
    baseline=(tmp_path/'baseline-reference.json').read_bytes()
    assert run('compare',url,tmp_path).returncode==0
    assert run('classify',url,tmp_path).returncode==0
    old_sha=digest(state['signal'])
    old_report=json.loads((tmp_path/'classification-report.json').read_text())
    state['signal']['all_breached_indicators']=['latency_p99_ratio']
    result=run('compare',url,tmp_path)
    assert result.returncode==0,result.stderr
    archives=list((tmp_path/'history'/old_sha).iterdir())
    assert len(archives)==1
    assert json.loads((archives[0]/'classification-report.json').read_text())==old_report
    assert digest(json.loads((archives[0]/'drift-signal.json').read_text()))==old_sha
    assert not (tmp_path/'classification-report.json').exists()
    assert not (tmp_path/'classification-receipt.json').exists()
    assert (tmp_path/'baseline-reference.json').read_bytes()==baseline
    state['reject_model']=True
    assert run('classify',url,tmp_path).returncode==2
    assert not (tmp_path/'classification-report.json').exists()
    assert (archives[0]/'classification-report.json').exists()


@pytest.mark.parametrize("tamper",["receipt","report"])
def test_tampered_prior_report_refuses_archive_and_alias_replacement(api,tmp_path,tamper):
    url,state=api
    assert run('reference',url,tmp_path).returncode==0
    assert run('compare',url,tmp_path).returncode==0
    assert run('classify',url,tmp_path).returncode==0
    previous=(tmp_path/'drift-signal.json').read_bytes()
    path=tmp_path/('classification-receipt.json' if tamper=='receipt' else 'classification-report.json')
    changed=json.loads(path.read_text())
    if tamper=='receipt':changed['input_sha256']='0'*64
    else:changed['recommendations']=[{'action':'Unreviewed altered prose'}]
    path.write_text(json.dumps(changed))
    state['signal']['all_breached_indicators']=[]
    result=run('compare',url,tmp_path)
    assert result.returncode!=0 and 'archive refused' in result.stderr
    assert (tmp_path/'drift-signal.json').read_bytes()==previous
    assert (tmp_path/'classification-report.json').exists()
    assert not (tmp_path/'history').exists()
