# Live controlled-workload path

The recorded core exercises teach evidence review without a cluster or model. The optional live path instead generates real HTTP requests against a deliberately controlled checkout app, scrapes its counters/histogram with namespaced Prometheus, collects measured windows with SLOscope, and optionally calls an approved real model. Controlled faults are lab-generated; they do not establish customer impact, service capacity, or a production incident.

## Provisioning boundary

The controller applies `automation/ansible/playbooks/lab.yml` to an existing isolated namespace. Inputs and security scope are described in the collection README. Use immutable approved engine and Prometheus images; the engine must contain interval-aware counter aggregation, window coverage checks, and configurable SLOSCOPE_LOOKBACK. Older collector images can start the sample app but must not be accepted for the live engine path.

No broad RBAC or outside exposure is required: only ClusterIP Services and same-lab ingress are created. Trusted operator permissions allow provisioning and pod-exec validation. Learner permissions are a separate proposed API/port-forward contract; learners must not receive container execution or Secret reads. No role binding is granted by this repo. The model Secret must be provisioned through the normal secret-management flow; do not copy an unrelated application credential or paste values into chat, YAML, or command arguments. The role only references the existing dedicated Secret.

Start telemetry with `sloscope_include_engine=false` if model access is pending. To qualify engine/PVC/collector behavior before the dedicated model Secret is ready, use `sloscope_include_engine=true` and `sloscope_require_model=false`. That explicit measurement-only profile makes Secret references optional and forbids model-validation helpers; with the Secret absent, live model requests return 503 instead of recorded fallback. This is model-optional startup and an operator workflow convention, not an API-level inference block: core does not enforce the helper flag, and a pre-existing Secret may bind even in the optional profile. Once the dedicated Secret exists, redeploy with `sloscope_require_model=true` to require and bind it. Use the final reviewed collector image for either engine profile. Deployment readiness does not prove a measured window exists. Let the configured lookback fill, inspect actual coverage, and rewarm after a Prometheus restart. The collector must reject insufficient coverage rather than backfill invented history.

## Private operator browser access

After the engine and its dedicated Secret are ready, an operator may forward its ClusterIP service to a loopback port on the same workstation as their browser:

```bash
oc -n <assigned-namespace> port-forward --address 127.0.0.1 service/sloscope 18080:8080
```

Keep that terminal open and visit `http://127.0.0.1:18080/dashboard/` from the same workstation. Stop the forward with Ctrl-C when finished. Do not bind it to 0.0.0.0 or publish it as an unauthenticated route. A port-forward inside a remote Showroom terminal is local to that terminal's host; it is not automatically reachable from the learner's browser. Published learner browser access requires its own reviewed OAuth/route integration.

## Real measurements and deliberate changes

`checkout.py` handles `/checkout` requests, records actual elapsed handler time, and exposes classic histogram buckets and `http_requests_total` with `service`, `namespace`, and `code` labels. The traffic process sends requests repeatedly; deliberate HTTP 503s remain counted. Prometheus scrapes every 10 seconds. No fixture response is served as live telemetry.

The `sloscope-scenario` ConfigMap controls the sample app's phase. Baseline/recovery use short handler delays and one controlled error per 50 requests. Regression uses longer delays and one error per 7 requests. The observed ratio and latency remain measured outcomes over a finite window; do not substitute these intended patterns for a measurement. ConfigMap projection can take time, and a comparison window may temporarily mix phases.

The app exposes no mutation endpoint. A learner changes the phase only through their authorized namespaced ConfigMap update. Restore baseline/recovery after the exercise. Do not reuse this control on a real service.

## Learner API sequence

Use `scripts/live-client.py` from the terminal host where the authorized loopback port-forward runs. It uses only Python's standard library, bypasses proxy settings for the loopback connection, refuses redirects/non-loopback targets, and receives no Kubernetes or model token. The Kubernetes connection authorizes the forward; the HTTP application remains a private unauthenticated service behind that local access path. Do not describe this as application OAuth authentication.

1. Confirm the assigned namespace, ready workloads, operator-provided image/source identity, and intended window. Open `oc port-forward --address 127.0.0.1 -n <assigned-namespace> service/sloscope 18080:8080` and keep it open in terminal 1. Use terminal 2 on the same host for API calls.
2. Run `python3.11 scripts/live-client.py check --namespace <assigned-namespace>`. It requires live mode and a matching canonical evidence digest, service/namespace, finite sufficient coverage, and measured request/histogram counts. This step makes no model call.
3. Run `reference` with the same flags. It requests server collection, reads the preserved baseline, and saves a canonical local reference and receipt in `.lab/live-learner/`. An existing local reference cannot be overwritten silently. A retained server reference needs provenance review rather than automatic replacement.
4. Patch only the named controlled scenario ConfigMap to regression. A successful patch changes desired configuration; allow asynchronous projection and the comparable collection window before interpreting measurements.
5. Run `compare`. It requires the server to preserve its reference, checks that baseline against the local digest, and saves the measured drift signal/receipt. Local or remote reference changes stop the workflow.
6. With explicit model approval, run `classify`. It submits the saved signal in live mode, requires matching header and evidence-constraint input digests plus the advisory policy, and saves the full report locally with a human-review receipt. Model rejection remains nonzero; no fixture is substituted.
7. Record the decision brief, restore the controlled scenario to recovery, and close the port-forward. The controller handles allocation teardown. Core local cleanup does not remove `.lab/live-learner/` or server PVC data; preserve receipts deliberately and remove them only when no longer needed.

The Showroom module contains the exact commands. Its cluster execution remains separate from fixture-only CI. Local protocol tests use an explicitly synthetic loopback test server to check digest mismatch, reference preservation/tampering, and nonzero model rejection; those tests do not establish real model or RBAC acceptance.

## Proposed catalog learner permission and credential contract

The review-only catalog handoff now emits an unbound proposed Role and runtime attributes; see `docs/catalog-handoff.md`. The deployment role still grants no permissions. Review the contract before binding it:

- Read assigned Deployment/Pod metadata and the named `sloscope` Service as required to find a ready allocation and forward the API.
- Permit the required `pods/portforward` operation only within the isolated allocation. Native RBAC selection for dynamic pod names and allocation isolation needs infrastructure review.
- Permit patch only on `configmaps` with `resourceNames: [sloscope-scenario]`; no arbitrary ConfigMap mutation.
- Exclude `pods/exec`, Secret reads, Deployment/image/environment mutation, workload creation, and unrelated subresources such as logs unless separately reviewed.
- Do not issue a shared namespace administrator identity and treat its successful walk as proof of regular-user enforcement.

No new Role or RoleBinding is added by this change. An operator can execute code in an engine pod and may inspect its environment; therefore Ansible exec validation and `/opt/sloscope-lab/{validate_live,classify_live}.py` are trusted-operator tooling only. They are not a safe learner credential boundary.

The authorized dev owner's shared model connection is not a qualified catalog design. Per-allocation MaaS credentials or a reviewed broker, quotas, revocation, data handling, and an independent regular-user walk remain PH infrastructure gates. An API client cannot enforce these server-side or Kubernetes permissions by itself.

## Open acceptance

Qualify actual restricted-SCC/PVC permissions, controller idempotence/ownership and teardown, real telemetry aggregation/coverage/missing-data, preserved references and drift, real model behavior/abstention, independent learner completion, alert firing/recovery, and PH content/infrastructure reviews. Eventually published learner access needs reviewed OAuth/route integration; this private dev contract does not add or claim that exposure.
