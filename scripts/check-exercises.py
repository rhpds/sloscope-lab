#!/usr/bin/env python3
"""Run the learner command sequence, asserting exact negative outcomes and artifacts."""
import json
import os
from pathlib import Path
import subprocess
import sys

if sys.flags.optimize:
    raise RuntimeError("Optimized Python is not supported for learner verification")
import tempfile

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='sloscope-lab-check-') as directory:
    def command(name,*extra,status=0,contains=None):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/labctl.py'),name,'--workdir',directory,*extra],
                              capture_output=True,text=True,env=os.environ.copy())
        assert result.returncode==status,(name,result.returncode,result.stdout,result.stderr)
        if contains:
            assert contains in result.stdout+result.stderr,(name,result.stdout,result.stderr)
        print('PASS:',name,*extra)
        return result
    command('prepare',contains='SYNTHETIC')
    command('baseline')
    command('baseline',status=1,contains='Reference already exists')
    command('drift',contains='Reference preserved')
    command('review',contains='admissible')
    command('low-coverage')
    command('review','--input',str(Path(directory)/'low-coverage-signal.json'),status=2,contains='At least 0.8 measured coverage')
    command('conflict')
    command('review','--input',str(Path(directory)/'conflicting-signal.json'),status=2,contains='Breached indicator list conflicts')
    command('export',status=2,contains='not an observed histogram bucket')
    command('export','--bucket-ms','1000',contains='targets still require human review')
    command('boundary',contains='default live mode returns 503')
    command('check',contains='2 abstentions')
    # Prove the final checkpoint fails if the preserved reference has changed.
    path=Path(directory)/'baseline.json'
    baseline=json.loads(path.read_text());baseline['service']='changed-service';path.write_text(json.dumps(baseline))
    command('check',status=1,contains='Reference changed')
print('All learner command checks passed; no real model/telemetry/cluster acceptance asserted')
