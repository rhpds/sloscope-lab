# Publishing House catalog handoff

This is an author review package for a Classic Showroom lab. Publishing House owns content/infrastructure approval, identity provisioning, AgnosticV generation and publication. No script in this package advances the workflow or grants access.

## Prepare one allocation

Save non-secret allocation inputs in a controller-local JSON file. Required fields are `namespace`, `user_name`, actual `openshift_version`, reviewed 40-character `content_revision`, digest-pinned `engine_image` and `prometheus_image`, and the existing `model_secret` name. Optional fields are `storage_class` and `lookback`. Unknown fields are rejected, including credential values. Use one isolated namespace per allocation. A content hash is a pin, not evidence of review; PH must confirm it exists in the selected repository and is approved.

```bash
python3.11 scripts/catalog-handoff.py --inputs /path/to/allocation-inputs.json > /path/to/review-package.json
```

The JSON contains:

- `allocation_vars` for the existing scoped Ansible playbook;
- `showroom_vars` with immutable content selection and the three runtime attributes used by the lessons;
- `resources` for operator review, without namespaces, credentials or RBAC grants;
- `proposed_learner_role`, deliberately unbound and excluded from the resources list;
- the budget derived from the deployment declarations and explicit remaining gates.

Do not apply the whole JSON as a Kubernetes manifest or put the review package into AgnosticV manually. The controller should consume the reviewed sections through Publishing House. Runtime substitution must render `project_namespace`, `user_name` and `openshift_version` in the actual Showroom allocation. The existing console tab uses the allocation domain; a shared-cluster terminal/console deployment must qualify that mapping. Local Antora placeholder rendering is not this acceptance.

## Learner identity and terminal

PH must approve a Role binding to the assigned learner identity. The proposed Role permits metadata reads, namespace-local pod forwarding and get/patch of only `sloscope-scenario`. It excludes Secret reads, pod execution, workload creation, deployment mutation and permission grants. Native pod forwarding permissions cover pods in the isolated namespace, not only the engine; do not place unrelated workloads or credentials there. Never use a namespace administrator identity to claim these boundaries passed.

Before entering the live module, run from the assigned terminal:

```bash
python3.11 scripts/check-learner-access.py --namespace YOUR_ASSIGNED_NAMESPACE
```

The preflight uses authorization queries and exits nonzero for missing rights, excessive tested rights, authentication errors or ambiguous results. It does not enumerate every possible permission or prove cluster isolation. Review all inherited roles separately. It checks generic Secret access and the specific model Secret name; supply `--model-secret` if the allocation uses a name other than `sloscope-model`. It reads no Secret, opens no shell and changes no configuration. Actual forwarding, scenario patching and HTTP collection still need the learner walk.

Two terminal sessions must share a writable checkout/workspace and loopback host. Verify Python 3.11, Git and `oc` before the pilot. One terminal holds the private forward while the other runs the HTTP client. A remote terminal's loopback address is not reachable from a desktop browser; the live terminal path requires no public application Route. Broader browser access would need a separate reviewed authentication design.

## Model ownership

Provision a dedicated model Secret through the approved allocation secret-management flow, with `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. The role references it and never creates, copies or deletes its values. The dev owner's connection must not become a shared catalog credential. PH must select per-allocation MaaS credentials or a reviewed broker, with issuer/owner, model access, quota, expiry, revocation, data handling and cleanup responsibilities recorded. Do not expose the credential in Showroom attributes, user data, Git, reports or learner commands.

## Capacity and release review

Current four-workload declarations request a total 400m CPU and 512 MiB memory, with aggregate limits of 4 CPU and 2048 MiB plus 1 GiB artifact storage. These are declared bounds, not capacity/load measurements; Showroom/terminal, shared infrastructure and remote model serving are excluded. Concurrency, node/cluster sizing and model capacity need infrastructure review. Prometheus retains two hours in ephemeral storage and must warm up after restart. Artifact PVCs are retained unless the operator explicitly requests removal; model credential revocation is a separate allocation-owner action.

The validated dev image is private to the dev registry. PH must select approved distributable digest-pinned images and pull access, storage class, supported cluster target and immutable content/source revisions. A catalog-supported release must be qualified separately from the private dev release. No public image, catalog release, RCARS result, content/infra approval or independent human completion is asserted by these preparations.
