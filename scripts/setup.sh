#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 -c 'import sys; assert sys.version_info[:2] == (3,11)'
engine_sha=$(python3.11 -c 'import json; print(json.load(open("engine.lock.json"))["commit"])')
[[ "$engine_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'engine.lock.json requires an immutable engine commit' >&2; exit 1; }
mkdir -p .lab
if [[ ! -d .lab/engine/.git ]]; then
  git clone https://github.com/jkershawrh/slo-sli-automation.git .lab/engine
fi
[[ -z "$(git -C .lab/engine status --porcelain)" ]] || { echo 'Preserve changes in .lab/engine before setup' >&2; exit 1; }
git -C .lab/engine fetch origin "$engine_sha"
git -C .lab/engine checkout --detach "$engine_sha"
python3.11 -m venv .lab/venv
.lab/venv/bin/python -m pip install --require-hashes -r .lab/engine/requirements.lock
printf '%s\n' 'Setup complete. Run .lab/venv/bin/python scripts/labctl.py prepare'
