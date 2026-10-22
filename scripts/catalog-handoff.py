#!/usr/bin/env python3
"""Prepare a non-secret allocation contract for PH review; never apply RBAC or catalog changes."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / 'automation/ansible/roles/sloscope_lab/files'
spec = importlib.util.spec_from_file_location('live_renderer', FILES / 'render.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
REQUIRED = {'namespace', 'user_name', 'openshift_version', 'content_revision', 'engine_image', 'prometheus_image', 'model_secret'}
OPTIONAL = {'storage_class', 'lookback'}


def prepare(inputs):
    if set(inputs) - REQUIRED - OPTIONAL or REQUIRED - set(inputs):
        raise ValueError('Supply exactly the documented non-secret allocation inputs; credentials are not accepted')
    if not all(isinstance(v, str) and v and not any(c in v for c in '\r\n\x00') for v in inputs.values()):
        raise ValueError('Allocation inputs must be nonempty single-line strings')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9@._-]{0,127}', inputs['user_name']):
        raise ValueError('Use the assigned learner user identity, not a token or group')
    if not re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?', inputs['openshift_version']):
        raise ValueError('Supply the actual allocation OpenShift version')
    if not re.fullmatch(r'[0-9a-f]{40}', inputs['content_revision']):
        raise ValueError('Select an immutable reviewed content commit, not a moving branch')
    namespace = inputs['namespace']
    manifest = renderer.render(namespace, inputs['engine_image'], inputs['prometheus_image'],
        model_secret=inputs['model_secret'], storage_class=inputs.get('storage_class', ''), lookback=inputs.get('lookback', '5m'))
    rules = [
        {'apiGroups': ['apps'], 'resources': ['deployments'], 'resourceNames': ['sloscope', 'checkout-api', 'checkout-traffic', 'sloscope-prometheus'], 'verbs': ['get']},
        {'apiGroups': [''], 'resources': ['pods'], 'verbs': ['get', 'list']},
        {'apiGroups': [''], 'resources': ['services'], 'resourceNames': ['sloscope'], 'verbs': ['get']},
        {'apiGroups': [''], 'resources': ['pods/portforward'], 'verbs': ['create']},
        {'apiGroups': [''], 'resources': ['configmaps'], 'resourceNames': ['sloscope-scenario'], 'verbs': ['get', 'patch']},
    ]
    role = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'Role',
        'metadata': {'name': 'sloscope-learner', 'namespace': namespace}, 'rules': rules}
    # Deliberately no RoleBinding: PH must select the isolated allocation identity and approve the grant.
    attrs = {'project_namespace': namespace, 'user_name': inputs['user_name'], 'openshift_version': inputs['openshift_version']}
    source = {'ocp4_workload_showroom_content_git_repo': 'https://github.com/rhpds/sloscope-lab',
        'ocp4_workload_showroom_content_git_repo_ref': inputs['content_revision'],
        'ocp4_workload_showroom_passthrough_user_data': True, 'ocp4_workload_showroom_user_data': attrs}
    allocation_vars = {'sloscope_namespace': namespace, 'sloscope_engine_image': inputs['engine_image'],
        'sloscope_prometheus_image': inputs['prometheus_image'], 'sloscope_model_secret': inputs['model_secret'],
        'sloscope_lookback': inputs.get('lookback', '5m'), 'sloscope_require_model': True}
    if inputs.get('storage_class'): allocation_vars['sloscope_storage_class'] = inputs['storage_class']
    deployments = [i for i in manifest['items'] if i['kind'] == 'Deployment']
    containers = [c for d in deployments for c in d['spec']['template']['spec']['containers']]
    cpu_request = sum(int(c['resources']['requests']['cpu'].removesuffix('m')) for c in containers)
    memory_request = sum(int(c['resources']['requests']['memory'].removesuffix('Mi')) for c in containers)
    return {'status': 'review_only_not_applied', 'allocation_vars': allocation_vars, 'showroom_vars': source,
        'proposed_learner_role': role, 'resources': manifest,
        'declared_per_allocation_budget': {'workloads': len(deployments), 'requested_cpu_millicores': cpu_request,
            'requested_memory_mib': memory_request, 'cpu_limit_cores': len(containers), 'memory_limit_mib': len(containers)*512,
            'persistent_artifact_gib': 1, 'excludes': ['Showroom/terminal overhead', 'cluster infrastructure', 'remote MaaS capacity', 'load qualification']},
        'review_gates': ['Content commit must be reviewed and present in the selected repository',
            'PH supplies isolated allocation namespace and a restricted terminal identity; no namespace admin',
            'PH approves and binds the proposed Role; this package grants no access',
            'Terminal sessions share a writable workspace and loopback host; verify oc and Python 3.11',
            'Model credential is issued per allocation or through an approved quota/revocation broker; existing Secret reference only',
            'Approve registry image distribution/pull access, storage, cluster version, concurrency and budget',
            'Render runtime attributes, run learner-access preflight and complete an independent learner pilot',
            'PH performs RCARS, content/infra review and AgnosticV generation; no approval inferred']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(json.loads(args.inputs.read_text())), indent=2))
    except (ValueError, TypeError, KeyError) as exc:
        parser.exit(2, str(exc)+'\n')

if __name__ == '__main__': main()
