"""Catalog preparation and authorization checks must fail closed without making grants."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def inputs():
    return {'namespace':'student-lab','user_name':'student1','openshift_version':'4.20.1',
        'content_revision':'a'*40,'engine_image':'registry.example/engine@sha256:'+'b'*64,
        'prometheus_image':'registry.example/prometheus@sha256:'+'c'*64,'model_secret':'allocation-model'}

def test_handoff_binds_immutable_content_runtime_attrs_and_existing_secret_only():
    m=load('catalog-handoff');r=m.prepare(inputs())
    assert r['status']=='review_only_not_applied'
    assert r['showroom_vars']['ocp4_workload_showroom_user_data']=={'project_namespace':'student-lab','user_name':'student1','openshift_version':'4.20.1'}
    assert r['showroom_vars']['ocp4_workload_showroom_content_git_repo_ref']=='a'*40
    assert r['allocation_vars']['sloscope_model_secret']=='allocation-model'
    assert r['declared_per_allocation_budget']['requested_cpu_millicores']==400
    assert r['declared_per_allocation_budget']['requested_memory_mib']==512
    objects=r['resources']['items']
    assert not any(x['kind'] in ('Secret','Role','RoleBinding','ClusterRole','ClusterRoleBinding','Namespace','Route') for x in objects)
    rules=r['proposed_learner_role']['rules']
    assert not any('secrets' in x['resources'] or 'pods/exec' in x['resources'] or '*' in x['verbs'] for x in rules)
    patch=[x for x in rules if 'patch' in x['verbs']]
    assert len(patch)==1 and patch[0]['resourceNames']==['sloscope-scenario']
    assert any('no namespace admin' in x for x in r['review_gates'])

@pytest.mark.parametrize('key,value',[('content_revision','main'),('engine_image','example:latest'),('namespace','default/other'),('user_name','system:admin'),('openshift_version','supplied-by-provisioning'),('LLM_API_KEY','secret')])
def test_handoff_refuses_mutable_refs_placeholder_attributes_and_secret_inputs(key,value):
    m=load('catalog-handoff');v=inputs();v[key]=value
    with pytest.raises(ValueError):m.prepare(v)

def test_access_preflight_checks_actual_subresources_and_detects_admin():
    m=load('check-learner-access');calls=[]
    def restricted(args,**kwargs):
        calls.append(args)
        deny=args[4] in ('secrets','pods','deployments.apps/sloscope','configmaps/sloscope-prometheus','rolebindings.rbac.authorization.k8s.io') and args[3] not in ('get','list')
        if args[4]=='secrets' or '--subresource=exec' in args:deny=True
        if '--subresource=portforward' in args:deny=False
        return SimpleNamespace(returncode=1 if deny else 0,stdout='no\n' if deny else 'yes\n')
    assert m.check('student-lab',restricted)['status']=='learner_access_qualified'
    assert any('--subresource=exec' in c for c in calls)
    assert any('--subresource=portforward' in c for c in calls)
    assert all(c[1:3]==['auth','can-i'] for c in calls)
    admin=lambda *a,**k:SimpleNamespace(returncode=0,stdout='yes\n')
    assert m.check('student-lab',admin)['status']=='learner_access_rejected'
    disconnected=lambda *a,**k:SimpleNamespace(returncode=1,stdout='')
    assert m.check('student-lab',disconnected)['checks'][0]['observed_allowed'] is None
