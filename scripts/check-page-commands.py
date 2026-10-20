#!/usr/bin/env python3
"""Execute the core lesson's literal shell blocks in a disposable learner workspace.

Setup/clone and the optional MCP dependency installation are separate qualification
steps. This check prevents the rendered lesson commands from drifting away from
the helper-only tests. It does not grade the learner's business recommendation.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

if sys.flags.optimize:
    raise RuntimeError('Optimized Python is not supported for learner verification')

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'content/modules/ROOT/pages'
LESSONS = (
    '03-evidence-and-reference.adoc',
    '04-drift-and-abstention.adoc',
    '05-review-and-export.adoc',
    '99-conclusion.adoc',
)


def main():
    source = ROOT / '.lab/engine'
    environment = ROOT / '.lab/venv'
    if not source.is_dir() or not environment.is_dir():
        raise RuntimeError('Run scripts/setup.sh before checking learner page commands')
    count = 0
    with tempfile.TemporaryDirectory(prefix='sloscope-page-walk-') as directory:
        workspace = Path(directory)
        shutil.copytree(ROOT / 'scripts', workspace / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(ROOT / 'engine.lock.json', workspace / 'engine.lock.json')
        (workspace / '.lab').mkdir()
        (workspace / '.lab/engine').symlink_to(source.resolve(), target_is_directory=True)
        (workspace / '.lab/venv').symlink_to(environment.resolve(), target_is_directory=True)
        env = os.environ.copy()
        env.pop('SLOSCOPE_SOURCE', None)
        run = subprocess.run([str(environment / 'bin/python'), str(workspace / 'scripts/labctl.py'), 'prepare'],
                             cwd=workspace, env=env, capture_output=True, text=True, timeout=60)
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
        for lesson in LESSONS:
            blocks = re.findall(r'\[source,role="execute"\]\n----\n(.*?)\n----', (PAGES / lesson).read_text(), re.S)
            if not blocks:
                raise RuntimeError(f'{lesson}: no executable lesson blocks found')
            for index, block in enumerate(blocks, 1):
                result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', block],
                                        cwd=workspace, env=env, capture_output=True, text=True, timeout=60)
                if result.returncode:
                    raise RuntimeError(f'{lesson} block {index} failed ({result.returncode})\n'
                                       + result.stdout + result.stderr)
                count += 1
                print(f'PASS: {lesson} block {index}')
        if (workspace / '.lab/learner').exists():
            raise RuntimeError('Conclusion cleanup did not remove the learner artifacts')
        if not (workspace / '.lab/engine').is_dir() or not (workspace / '.lab/venv').is_dir():
            raise RuntimeError('Conclusion cleanup removed the engine or environment')
    print(f'PASS: {count} literal core lesson blocks, capstone checkpoint and scoped cleanup; decision brief requires human review')


if __name__ == '__main__':
    main()
