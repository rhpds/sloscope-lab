"""Offline contract safety plus a real HTTP/metrics exercise of the controlled workload."""
import importlib.util
from pathlib import Path
import threading
from urllib.request import urlopen
from urllib.error import HTTPError

import pytest

ROOT=Path(__file__).resolve().parents[1]
FILES=ROOT/'automation/ansible/roles/sloscope_lab/files'


def module(name):
    spec=importlib.util.spec_from_file_location(name,FILES/(name+'.py'))
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_manifest_contract_scopes_resources_and_requires_immutable_images():
    renderer=module('render')
    engine='example.com/sloscope@sha256:'+'a'*64
    prometheus='example.com/prometheus@sha256:'+'b'*64
    with pytest.raises(ValueError,match='immutable'):
        renderer.render('lab-user','example.com/sloscope:latest',prometheus)
    with pytest.raises(ValueError,match='Kubernetes DNS label'):
        renderer.render('default/other',engine,prometheus)
    result=renderer.render('lab-user',engine,prometheus)
    allowed={'ConfigMap','PersistentVolumeClaim','Deployment','Service','NetworkPolicy'}
    assert {item['kind'] for item in result['items']}<=allowed
    for item in result['items']:
        assert item['metadata']['namespace']=='lab-user'
        assert item['metadata']['labels']['app.kubernetes.io/managed-by']=='sloscope-lab'
        if item['kind']=='Service':
            assert item['spec']['type']=='ClusterIP'
            assert not item['spec'].get('externalIPs')
        if item['kind']=='Deployment':
            pod=item['spec']['template']['spec']
            assert pod['automountServiceAccountToken'] is False
            assert not pod.get('hostNetwork')
            assert all('hostPath' not in volume for volume in pod['volumes'])
            for container in pod['containers']:
                assert '@sha256:' in container['image']
                security=container['securityContext']
                assert security['allowPrivilegeEscalation'] is False
                assert security['runAsNonRoot'] is True
                assert security['capabilities']['drop']==['ALL']
    engine_pod=next(item for item in result['items'] if item['kind']=='Deployment' and item['metadata']['name']=='sloscope')
    env={row['name']:row for row in engine_pod['spec']['template']['spec']['containers'][0]['env']}
    assert env['SLOSCOPE_SEED_DEMO']['value']=='false'
    assert env['SLOSCOPE_LOOKBACK']['value']=='5m'
    for key in ('LLM_BASE_URL','LLM_API_KEY','LLM_MODEL'):
        assert env[key]['valueFrom']['secretKeyRef']=={'name':'sloscope-model','key':key,'optional':False}
        assert 'value' not in env[key]
    measured=renderer.render('lab-user',engine,prometheus,require_model=False)
    measured_engine=next(item for item in measured['items'] if item['kind']=='Deployment' and item['metadata']['name']=='sloscope')
    measured_env={row['name']:row for row in measured_engine['spec']['template']['spec']['containers'][0]['env']}
    assert measured_env['SLOSCOPE_REQUIRE_MODEL']['value']=='false'
    assert all(measured_env[key]['valueFrom']['secretKeyRef']['optional'] for key in ('LLM_BASE_URL','LLM_API_KEY','LLM_MODEL'))
    telemetry=renderer.render('lab-user',engine,prometheus,include_engine=False)
    assert len([item for item in telemetry['items'] if item['kind']=='Deployment'])==3
    assert not any(item['kind']=='PersistentVolumeClaim' for item in telemetry['items'])
    assert not any(item['kind']=='Deployment' and item['metadata']['name']=='sloscope' for item in telemetry['items'])


def test_controlled_checkout_emits_real_request_counts_and_histogram(tmp_path,monkeypatch):
    phase=tmp_path/'phase'
    phase.write_text('baseline')
    monkeypatch.setenv('POD_NAMESPACE','lab-user')
    monkeypatch.setenv('SLOSCOPE_SCENARIO_FILE',str(phase))
    app=module('checkout')
    server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    statuses=[]
    try:
        with urlopen(base+'/health') as response:
            assert response.status==200
        for _ in range(50):
            try:
                with urlopen(base+'/checkout') as response:
                    statuses.append(response.status)
            except HTTPError as response:
                statuses.append(response.code)
        assert statuses.count(503)==1
        phase.write_text('regression')
        for _ in range(7):
            try:
                with urlopen(base+'/checkout') as response:
                    statuses.append(response.status)
            except HTTPError as response:
                statuses.append(response.code)
        assert statuses.count(503)==2
        with urlopen(base+'/metrics') as response:
            metrics=response.read().decode()
        assert 'http_requests_total{service="checkout-api",namespace="lab-user",code="200"} 55' in metrics
        assert 'http_requests_total{service="checkout-api",namespace="lab-user",code="503"} 2' in metrics
        assert 'http_request_duration_seconds_count{service="checkout-api",namespace="lab-user"} 57' in metrics
        assert 'le="+Inf"} 57' in metrics
        assert app.SUM>0
        assert app.HIST[.1]==50 and app.HIST[.5]==57
        assert all(a<=b for a,b in zip(app.HIST.values(),list(app.HIST.values())[1:]))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_source_checksums_roll_out_code_without_restarting_on_phase_changes(tmp_path,monkeypatch):
    renderer=module('render')
    images=('example.com/engine@sha256:'+'a'*64,'example.com/prometheus@sha256:'+'b'*64)
    def annotations(result):
        return {item['metadata']['name']:item['spec']['template']['metadata']['annotations']
                for item in result['items'] if item['kind']=='Deployment'}
    baseline=annotations(renderer.render('lab-user',*images))
    regression=annotations(renderer.render('lab-user',*images,scenario_phase='regression'))
    assert baseline==regression  # Deliberate phase changes must preserve process/counter continuity.
    for source in FILES.glob('*.py'):
        (tmp_path/source.name).write_text(source.read_text())
    (tmp_path/'checkout.py').write_text((tmp_path/'checkout.py').read_text()+'\n# reviewed source update\n')
    monkeypatch.setattr(renderer,'ROOT',tmp_path)
    updated=annotations(renderer.render('lab-user',*images))
    assert baseline['checkout-api']!=updated['checkout-api']
    assert baseline['checkout-traffic']!=updated['checkout-traffic']
    assert baseline['sloscope']!=updated['sloscope']
    assert baseline['sloscope-prometheus']==updated['sloscope-prometheus']
