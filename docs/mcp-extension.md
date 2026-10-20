# Optional MCP protocol exercise

The optional adapter is pinned separately because its draft PR is stacked on the core engine PR. Core exercises use `engine.lock.json`; this extension uses `mcp.lock.json`. Review both PRs before enabling an RHDP learner environment.

- Core fixes: https://github.com/jkershawrh/slo-sli-automation/pull/13
- MCP adapter: https://github.com/jkershawrh/slo-sli-automation/pull/14
- MCP source: `4ae814545419cb8f1077f399b135002fa6775f5c`
- SDK: `mcp==2.3.0`, installed only in `.lab/mcp-venv`

From the lab repository root, after completing the core exercises:

```bash
bash scripts/setup-mcp.sh
.lab/mcp-venv/bin/python scripts/check-mcp.py
```

The setup checks out exactly the adapter commit and installs its core hashed requirements plus the pinned optional MCP requirement. The optional SDK's transitive dependency set is resolved at installation; qualify and pre-seed that environment before RHDP delivery. Core setup does not install MCP.

The protocol check starts a real local stdio server through the SDK, initializes a client, lists exactly four tools with read-only/no-destructive/no-open-world annotations, checks the lab's admissible drift input, and confirms low-coverage abstention. It also checks that tool inputs do not expose file, command, URL, or credential parameters. It makes no real model or telemetry calls and does not install anything into an assistant host.

Expected final result:

```
PASS: discovered 4 bounded tools; real stdio review admitted measured evidence and abstained on low coverage
```

The process closes with the client session. No listening network port, cluster login, API key, or production telemetry is required. Use the engine's `docs/MCP.md` for generic host configuration, privacy considerations, and the wider protocol tests. Host configuration requires its own review; successful local protocol exchange is not independent host or RHDP deployment acceptance.
