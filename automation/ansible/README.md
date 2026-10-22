# Namespace-scoped live lab contract

`roles/sloscope_lab` implements deploy, validate, and teardown for an existing isolated namespace. It starts a controlled checkout workload, real HTTP traffic, a private Prometheus scrape, and optionally the SLOscope engine with persistent artifacts and an existing dedicated model Secret. The old example entry point delegates to this role.

Use `playbooks/lab.yml` from the repository checkout. Install the pinned `kubernetes.core` collection in requirements.yml into the controller's normal approved environment. Kubernetes Python client dependencies are also required by that collection. Set `KUBECONFIG` locally; never put credentials in this repository or command arguments.

## Inputs

- `sloscope_action`: `deploy`, `validate`, or `teardown`.
- `sloscope_namespace`: existing isolated namespace; no namespace is created or deleted.
- `sloscope_engine_image`: immutable `registry/repository@sha256:...`; used for the engine and stdlib sample/traffic containers.
- `sloscope_prometheus_image`: immutable image digest. Both images are mandatory for deploy.
- `sloscope_include_engine`: true by default. False deploys only controlled telemetry, allowing its window to warm up while a dedicated model Secret is prepared. No model Secret or PVC is required in that mode.
- `sloscope_require_model`: true by default. False starts a measurement-only engine/PVC with optional Secret references and skips Secret preflight, so telemetry can be qualified while the user prepares a dedicated credential. Model validation/interpretation helpers reject this profile. With no Secret, a direct live model request returns 503, never a fixture. After the dedicated Secret exists, redeploy with true to bind/require it and restart the engine. This is a startup/workflow profile, not an API authorization boundary: the core does not enforce SLOSCOPE_REQUIRE_MODEL. If the Secret already exists, optional references can bind it and direct API calls may infer; the helper refusal is narrower. No credentials are created or copied.
- `sloscope_model_secret`: existing Secret name, default `sloscope-model`, with `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. This role does not create, copy, print, or delete its values. Required only when the engine is included.
- `sloscope_storage_class`: optional storage class; default cluster selection otherwise. The artifact PVC requests 1 GiB, RWO.
- `sloscope_lookback`: `5m` by default; accepted explicit lab windows are 5m/10m/15m/30m/1h. The supplied engine image must implement `SLOSCOPE_LOOKBACK` and interval-aware collector fixes before live acceptance.
- `sloscope_scenario_phase`: baseline/regression/recovery, initially baseline. Reapplying deploy applies this chosen phase; do not redeploy during an experiment without preserving the intended phase.
- `sloscope_validate_model`: false by default. True explicitly requests a real live proposal during validate, after telemetry passes; rejection/failure remains a failure.
- `sloscope_remove_artifacts`: false by default. Teardown retains the artifact PVC unless this is explicitly true. Namespace and model Secret are always retained.

Example controller invocation, with non-secret inputs saved in a local reviewed vars file:

```bash
ansible-playbook automation/ansible/playbooks/lab.yml -e @/path/to/reviewed-lab-inputs.yml -e sloscope_action=deploy
ansible-playbook automation/ansible/playbooks/lab.yml -e @/path/to/reviewed-lab-inputs.yml -e sloscope_action=validate
ansible-playbook automation/ansible/playbooks/lab.yml -e @/path/to/reviewed-lab-inputs.yml -e sloscope_action=teardown
```

The renderer is also usable without Ansible; `python3 scripts/render-live.py --help` describes the same inputs. A rendered manifest is not a validated allocation. Only apply it after reviewing the selected namespace, image digests, and ownership; direct apply does not perform the role's collision or Secret preflight checks.

## Scope and security

Only namespaced ConfigMaps, Deployments, ClusterIP Services, an artifact PVC, and an ingress NetworkPolicy are created. No ClusterRole/RoleBinding, service-account token mount, host networking, host volume, external Service, Ingress, or Route is requested. Containers drop capabilities, use non-root execution and read-only root filesystems, and have bounded CPU/memory requests/limits. Same-lab pods in the same namespace may connect; egress is not restricted because DNS/model access needs a separately reviewed policy. There is no unauthenticated external application endpoint. Pod-exec validation is trusted-operator-only: engine execution can expose model environment credentials. Learners instead use the local HTTP client through an authorized loopback port-forward, without exec or Secret reads. PH must review/enforce that regular-user permission and per-allocation credential contract and eventual OAuth exposure separately.

Prometheus uses a static scrape and no Kubernetes API discovery. Its short 2-hour TSDB is ephemeral: a pod restart loses telemetry history and requires a new warm-up. Artifact storage is persistent and is retained by default. These are dev-lab choices, not full availability or backup guarantees.

The Prometheus ConfigMap includes an initially empty qualification-rules file and its rule_files entry. Projected ConfigMap updates do not automatically reload Prometheus: an authorized operator must confirm projection and send SIGHUP or perform a planned restart. No HTTP lifecycle mutation endpoint is enabled. Reapplying deploy restores the renderer’s empty qualification rules and selected scenario phase; preserve or deliberately finish an operator qualification experiment before redeploying.

The role refuses to adopt named resources without its ownership label. Teardown selects only `app.kubernetes.io/managed-by=sloscope-lab` resources in the requested namespace. Use one lab allocation per namespace; that label denotes the ownership boundary. Teardown removes the allocation's managed resources regardless of the include-engine deploy setting, but preserves the PVC unless explicitly asked to remove it.

## What validation establishes

Deploy waits for workload readiness. Validate with `sloscope_include_engine=false` checks actual scrape health and nonzero controlled request counters. Full validate checks collection identity, coverage, measured counts, and a computed baseline through the live HTTP path. Model invocation is a separate opt-in and requires a nonempty, evidence-constrained live proposal with human-review flags. `qa-automation/live.yml` invokes this same trusted-operator validation contract. Its pod-exec capability is not a learner permission grant. Root's live evidence, independent learner acceptance, alert firing, and PH review remain separate gates; local renderer/HTTP tests are not deployment proof.

See `docs/live-lab.md` and the optional Showroom live module for learner and operator sequencing.

## Publishing House handoff

Use `scripts/catalog-handoff.py` and `docs/catalog-handoff.md` to prepare immutable allocation inputs, Showroom runtime attributes, declared budgets and an unbound proposed learner Role for review. The deployment playbook does not apply that Role or create a binding. Run the authorization-only learner preflight before the live lesson. Credential issuance, binding approval and AgnosticV generation stay with PH.
