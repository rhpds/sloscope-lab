"""The learner may forward only after all named workloads meet readiness."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness', ROOT / 'scripts/check-learner-readiness.py')
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


def deployment(name):
    return {'metadata': {'name': name, 'namespace': 'student-lab', 'generation': 2},
        'spec': {'replicas': 1}, 'status': {'observedGeneration': 2, 'replicas': 1,
        'updatedReplicas': 1, 'readyReplicas': 1, 'availableReplicas': 1}}


class Clock:
    now = 0
    def clock(self): return self.now
    def sleep(self, delay): self.now += delay


def run_check(mutate=None, recover=False):
    calls = []
    clock = Clock()
    def run(args, **kwargs):
        calls.append(args)
        assert args[1] == 'get' and args[2].startswith('deployments.apps/')
        assert args[3:] == ['--namespace', 'student-lab', '-o', 'json', '--request-timeout=10s']
        obj = deployment(args[2].split('/')[1])
        if mutate and (not recover or clock.now == 0):
            mutate(obj)
        return SimpleNamespace(returncode=0, stdout=json.dumps(obj))
    result = readiness.wait_ready('student-lab', 3, run, clock.sleep, clock.clock)
    return result, calls, clock.now


def test_four_ready_workloads_pass_with_only_existing_named_reads():
    result, calls, _ = run_check()
    assert result['status'] == 'learner_workloads_ready'
    assert len(calls) == 4


@pytest.mark.parametrize('mutation', [
    lambda d: d['status'].update(observedGeneration=1),
    lambda d: d['status'].update(updatedReplicas=0),
    lambda d: d['status'].update(readyReplicas=0),
    lambda d: d['status'].update(availableReplicas=0),
    lambda d: d['status'].update(replicas=2),
    lambda d: d['spec'].update(replicas=0),
    lambda d: d['metadata'].update(deletionTimestamp='2026-10-22T00:00:00Z'),
    lambda d: d['metadata'].update(namespace='other-allocation'),
])
def test_unready_stale_scaled_down_and_wrong_allocation_fail_at_deadline(mutation):
    result, _, elapsed = run_check(mutation)
    assert result['status'] == 'learner_workloads_not_ready'
    assert elapsed == 3


def test_gate_waits_for_recovery_within_bound():
    result, calls, elapsed = run_check(lambda d: d['status'].update(readyReplicas=0), recover=True)
    assert result['status'] == 'learner_workloads_ready'
    assert elapsed == 2 and len(calls) == 8


def test_read_failure_cannot_count_as_readiness():
    def denied(*args, **kwargs): return SimpleNamespace(returncode=1, stdout='')
    with pytest.raises(ValueError, match='Cannot read named Deployment'):
        readiness.wait_ready('student-lab', run=denied)


def test_lesson_chains_both_gates_before_loopback_forward():
    text = (ROOT / 'content/modules/ROOT/pages/07-live-lab.adoc').read_text()
    command = text.split('In terminal 1:', 1)[1].split('----')[1]
    assert command.index('check-learner-access.py') < command.index('check-learner-readiness.py') < command.index('oc port-forward')
    assert command.count('&&') == 2
    assert '--address 127.0.0.1' in command
