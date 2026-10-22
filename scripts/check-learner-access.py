#!/usr/bin/env python3
"""Check the current oc identity's allocation permissions; no grants, token reads or mutations."""
import argparse
import json
import subprocess
import sys
import re


def check(namespace, run=subprocess.run, model_secret="sloscope-model"):
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', namespace):
        raise ValueError('Use the assigned namespace DNS label')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', model_secret):
        raise ValueError('Use the configured model Secret name')
    cases = []
    for name in ('sloscope', 'checkout-api', 'checkout-traffic', 'sloscope-prometheus'):
        cases.append(('get', 'deployments.apps/'+name, True))
    cases += [('list', 'pods', True), ('get', 'services/sloscope', True),
        ('create', 'pods/portforward', True), ('get', 'configmaps/sloscope-scenario', True),
        ('patch', 'configmaps/sloscope-scenario', True), ('get', 'secrets', False),
        ('list', 'secrets', False), ('get', 'secrets/'+model_secret, False), ('create', 'pods/exec', False), ('create', 'pods', False),
        ('patch', 'deployments.apps/sloscope', False), ('patch', 'configmaps/sloscope-prometheus', False),
        ('create', 'rolebindings.rbac.authorization.k8s.io', False)]
    results = []
    for verb, resource, expected in cases:
        target = resource
        subresource = []
        if resource in ('pods/portforward', 'pods/exec'):
            target, sub = resource.split('/')
            subresource = ['--subresource='+sub]
        p = run(['oc', 'auth', 'can-i', verb, target, '--namespace', namespace] + subresource, capture_output=True, text=True, timeout=30)
        observed = p.stdout.strip()
        # Connection/auth errors and unexpected output never count as an observed denial.
        valid = (p.returncode == 0 and observed == 'yes') or (p.returncode == 1 and observed == 'no')
        results.append({'verb': verb, 'resource': resource, 'expected_allowed': expected,
            'observed_allowed': observed == 'yes' if valid else None, 'pass': valid and (observed == 'yes') == expected})
    return {'status': 'learner_access_qualified' if all(r['pass'] for r in results) else 'learner_access_rejected',
        'namespace': namespace, 'checks': results, 'scope': 'authorization queries only; no port-forward, Secret read, shell or scenario mutation performed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--model-secret', default='sloscope-model')
    args = parser.parse_args()
    try: result = check(args.namespace, model_secret=args.model_secret)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, type(exc).__name__+': learner permission check could not complete\n')
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'learner_access_qualified' else 1)

if __name__ == '__main__': main()
