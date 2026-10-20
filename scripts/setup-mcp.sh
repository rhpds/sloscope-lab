#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 -c 'import sys; assert sys.version_info[:2] == (3,11)'
engine_sha=$(python3.11 -c 'import json; print(json.load(open("mcp.lock.json"))["commit"])')
[[ "$engine_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'mcp.lock.json requires an immutable adapter commit' >&2; exit 1; }
mkdir -p .lab
if [[ ! -d .lab/mcp-engine/.git ]]; then
  git clone https://github.com/jkershawrh/slo-sli-automation.git .lab/mcp-engine
fi
[[ -z "$(git -C .lab/mcp-engine status --porcelain)" ]] || { echo 'Preserve changes in .lab/mcp-engine before setup' >&2; exit 1; }
git -C .lab/mcp-engine fetch origin "$engine_sha"
git -C .lab/mcp-engine checkout --detach "$engine_sha"
python3.11 -m venv .lab/mcp-venv
.lab/mcp-venv/bin/python -m pip install --require-hashes -r .lab/mcp-engine/requirements.lock
.lab/mcp-venv/bin/python -m pip install -r .lab/mcp-engine/requirements-mcp.txt
printf '%s\n' 'MCP environment ready. Run .lab/mcp-venv/bin/python scripts/check-mcp.py'
