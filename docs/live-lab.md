# Live controlled-workload path

The recorded core exercises teach evidence review without a cluster or model. The optional live path instead generates real HTTP requests against a deliberately controlled checkout app, scrapes its counters/histogram with namespaced Prometheus, collects measured windows with SLOscope, and optionally calls an approved real model. Controlled faults are lab-generated; they do not establish customer impact, service capacity, or a production incident.

## Provisioning boundary

The controller applies `automation/ansible/playbooks/lab.yml` to an existing isolated namespace. Inputs and security scope are described in the collection README. Use immutable approved engine and Prometheus images; the engine must contain interval-aware counter aggregation, window coverage checks, and configurable SLOSCOPE_LOOKBACK. Older collector images can start the sample app but must not be accepted for the live engine path.

No broad RBAC or outside exposure is required: only ClusterIP Services and same-lab ingress are created. Existing namespace-scoped permissions must allow the controller to operate these resources and the learner to read/exec their own pods and patch the controlled scenario. No role binding is granted by this repo. The model Secret must be provisioned through the normal secret-management flow; do not copy an unrelated application credential or paste values into chat, YAML, or command arguments. The role only references the existing dedicated Secret.

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

## Learner sequence

1. Confirm the assigned namespace, running workloads, engine source/image identity, and configured window. Run the live validation helper; stop on missing coverage or identity errors.
2. Collect and persist the first reference through `python -m backend.collector --service checkout-api --namespace <assigned-namespace>` inside the engine pod. Record the baseline file hash. A retained artifact PVC may already contain a reference; use its provenance or request a fresh allocation rather than silently replacing it.
3. Change the controlled scenario to regression. Wait for the projected phase and a comparable collection window. Keep the traffic generator running.
4. Collect again. The stored reference must remain unchanged; inspect current-baseline and drift-signal. A changed reference or an insufficient/contradictory signal blocks the next step.
5. If real model access is explicitly enabled, run `/opt/sloscope-lab/classify_live.py --namespace <assigned-namespace>` inside the engine pod. It submits the persisted signal to the live HTTP endpoint, requires a matching input digest/live header, and stores a validated report. Rejected/failed execution remains nonzero; no recorded response is substituted.
6. Keep measured facts, policy admission, and model prose distinct in the decision brief. Restore recovery and leave artifact/cluster cleanup to the reviewed controller workflow.

The Showroom optional live module contains the exact learner commands. Its execution requires a provisioned allocation and is intentionally excluded from the fixture-only CI walk. The standalone local test verifies only the sample's real loopback HTTP counters/histogram and manifest scope. Cluster/model evidence must be attached separately before marking those gates complete.

## Open acceptance

Qualify actual restricted-SCC/PVC permissions, controller idempotence/ownership and teardown, real telemetry aggregation/coverage/missing-data, preserved references and drift, real model behavior/abstention, independent learner completion, alert firing/recovery, and PH content/infrastructure reviews. Eventually published learner access needs reviewed OAuth/route integration; this private dev contract does not add or claim that exposure.
