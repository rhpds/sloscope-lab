#!/usr/bin/env python3
"""Bounded readiness gate using only the learner's four named Deployment reads."""
import argparse
import json
import math
import re
import subprocess
import sys
import time

DEPLOYMENTS = ('sloscope', 'checkout-api', 'checkout-traffic', 'sloscope-prometheus')


def wait_ready(namespace, timeout=120, run=subprocess.run, sleep=time.sleep, clock=time.monotonic):
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', namespace):
        raise ValueError('Use the assigned namespace DNS label')
    if not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('Readiness timeout must be between zero and 600 seconds')
    deadline = clock() + timeout
    checks = []
    while clock() < deadline:
        checks = []
        for name in DEPLOYMENTS:
            remaining = deadline - clock()
            if remaining <= 0:
                return {'status': 'learner_workloads_not_ready', 'namespace': namespace, 'checks': checks}
            result = run(['oc', 'get', 'deployments.apps/' + name, '--namespace', namespace,
                          '-o', 'json', '--request-timeout=10s'],
                         capture_output=True, text=True, timeout=min(10, remaining))
            if result.returncode != 0:
                raise ValueError('Cannot read named Deployment ' + name + '; facilitator repair required')
            obj = json.loads(result.stdout)
            meta, spec, status = obj.get('metadata', {}), obj.get('spec', {}), obj.get('status', {})
            generation = meta.get('generation', 0)
            desired = spec.get('replicas', 1)
            counts = {k: status.get(k, 0) for k in ('replicas', 'updatedReplicas', 'readyReplicas', 'availableReplicas')}
            ready = (meta.get('name') == name and meta.get('namespace') == namespace
                     and not meta.get('deletionTimestamp') and generation > 0
                     and status.get('observedGeneration', 0) >= generation and desired > 0
                     and all(value == desired for value in counts.values()))
            checks.append({'deployment': name, 'ready': ready, 'desired': desired,
                           'generation': generation, 'observed_generation': status.get('observedGeneration', 0),
                           **counts})
        if all(check['ready'] for check in checks):
            return {'status': 'learner_workloads_ready', 'namespace': namespace, 'checks': checks}
        remaining = deadline - clock()
        if remaining > 0:
            sleep(min(2, remaining))
    return {'status': 'learner_workloads_not_ready', 'namespace': namespace, 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    try:
        result = wait_ready(args.namespace, args.timeout)
    except (ValueError, TypeError, OSError, subprocess.TimeoutExpired):
        parser.exit(2, 'Learner workload readiness could not be verified; ask the facilitator to repair the allocation.\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'learner_workloads_ready' else 1


if __name__ == '__main__':
    sys.exit(main())
