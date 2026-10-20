# RHDP delivery contract and open gates

This PR supplies Showroom content, deterministic exercises, a source lock, checks, and a scoped live deployment contract. Local manifest/HTTP checks do not establish an accepted RHDP allocation; live dev evidence and remaining gates are recorded separately.

## Proposed learner environment

Use an OpenShift-hosted Classic Showroom with a terminal and embedded console. Give each learner an isolated writable workspace, Python 3.11, Git, and the pinned engine/dependencies. The core synthetic path needs no model, Kubernetes credential, monitoring permission, or GPU. Setup downloads public source and Python packages; production delivery should pre-seed approved immutable artifacts to avoid first-run network drift.

The live extension is a separate qualification scope: read access to the learner service's real Prometheus/Thanos series with verified TLS; service and namespace label mappings; declared coverage semantics; a supported open-weight model endpoint; scoped secret injection; and persistent artifact storage. Keep model credentials server-side and out of learner pages. Define OAuth protection and PVC ownership before exposing the API. Do not derive defaults for unknown CPU/memory limits or use a broad administrator token.

Topology, cluster release, worker sizing, per-user limits, concurrency, image digests, model identity, cost, and base catalog remain **pending infrastructure review**. The spec leaves these unverified values unset. Proposed OpenShift hosting does not establish a tested version. RHDP must supply `{openshift_version}`, `{user_name}`, and `{project_namespace}` at runtime.

## Reviewer acceptance

1. Review and merge the pinned core engine fixes and optional MCP adapter before final source qualification. Re-run content checks when source references change.
2. Render every page, verify terminal/console tabs and runtime attribute substitution, and independently complete the commands as a regular learner.
3. Qualify the implemented namespace-scoped Ansible deploy/validate/teardown contract, controller ownership/idempotence, and restricted-user storage. See docs/live-lab.md; the old example now delegates to the implemented role. Learner access and final PH provisioning still need acceptance.
4. Execute `qa-automation/healthcheck.yml` and `e2e.yml` with actual provisioned source/runtime paths. Those checks cover synthetic review only; qa-automation/live.yml separately exercises measured controlled telemetry and optional real model execution. Attach each result under its actual scope.
5. Qualify collection against real label mappings and windows, preserved reference behavior, model failures/abstention, numeric claims, and secret handling. Synthetic fixtures are not this evidence.
6. Test Prometheus alert firing, recovery, and missing-data cases; validate OpenSLO in a real consumer. CPU/memory alert binding is currently unsupported.
7. Review the optional MCP source/host, confirm real protocol discovery and abstention, and verify no unsupported tool access. A local SDK test does not establish host deployment acceptance.
8. Review teardown of learner artifacts and allocation resources, tested immutable images, resource sizing, and operating ownership. Do not remove shared resources in learner cleanup.
9. Complete Publishing House RCARS/content/infrastructure gates. Publishing House owns AgnosticV generation and RHDP onboarding; this PR does not edit catalogs directly or advance workflow state.

## Evidence classification

Locally reproducible: synthetic artifact math, preservation/rejection checkpoints, in-process HTTP boundaries, stdio protocol (when adapter enabled), Antora structure/render, and link checks.

Still external: live telemetry integrity and coverage, real-model behavior, alert firing, cluster installation/security, runtime Showroom attributes/tabs, independent learner acceptance, workflow approvals, and RHDP publication.

## Content build dependency follow-up

The pinned Antora 3.2.0 build dependency tree currently reports 8 high registry findings through the unfixed `braces` stack-exhaustion advisory (GHSA-vfj7-8cjw-p6xm). These are content-build dependencies, not deployed SLOscope runtime packages. A compatible audit fix did not remove them; no patched transitive version is currently offered by the registry. Keep build input and credentials restricted, monitor the upstream fix, and refresh/retest the lock when a patch is available. This PR does not claim a clean dependency audit.

## Content checkout and learner-walk qualification

The current review instructions select `codex/sloscope-showroom-lab` explicitly because main remains the PH scaffold. Before publication, provision a reviewed immutable content revision as well as the pinned engine and optional adapter. Do not distribute a moving draft branch as a released lab. Antora cleans its output directory so renamed pages cannot remain reachable as stale lessons. CI checks helper outcomes and literal core lesson blocks separately; fresh setup, optional protocol, rendered reading and the human decision brief also need acceptance.

## Learner credential boundary

Trusted operator pod-exec checks are distinct from the learner path because executing inside a model-enabled container can expose its environment credentials. The live learner now uses scripts/live-client.py over an authorized loopback port-forward, with no engine exec or Secret reads. This change documents but does not implement the proposed minimal RBAC and per-allocation MaaS token/broker contract in docs/live-lab.md. Current dev-owner success does not qualify a catalog learner identity or shared model token.
