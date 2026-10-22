# Review live controlled telemetry

## Brief Overview

Extend the checkout owner's decision brief with actual controlled-workload measurements. The learner distinguishes a requested fault from an observed change and a constrained model report from verified cause. The core synthetic path remains usable without this extension.

## Audience and Time

Intermediate SRE/platform engineers; 45 minutes, author estimate pending a human pilot. Complete the core concepts first. A provisioned isolated allocation, reviewed source/image identity, restricted terminal credentials and two sessions on the same loopback host are prerequisites. Collection windows and asynchronous scenario projection require real elapsed time.

## Learning Objectives

- Check required and forbidden tested permissions before forwarding the private API.
- Verify live provenance, scope, measured coverage and a preserved reference.
- Compare a deliberately changed window without rewriting the reference.
- Optionally review an input-bound real-model classification with explicit failure/abstention and human-review boundaries.
- Restore the controlled scenario and use fresh measurements to verify recovery.

## Lab Structure and Steps

Use `content/modules/ROOT/pages/07-live-lab.adoc`. Inspect the business question and predict what must happen before a changed window is comparable. Run the access preflight; stop for facilitator repair if it fails. Hold an authenticated loopback forward in terminal 1 and use the learner HTTP client in terminal 2. Preserve the reference, patch only the named controlled scenario, inspect the measured comparison and optionally request classification. Rejection remains visible and cannot become a recorded fallback or a previous report presented as current. Restore recovery and record fresh evidence, coverage, reference identity and uncertainty in the decision brief. Close the forward; allocation teardown is an operator responsibility.

## Key Takeaways

A running pod is not a measured window, a requested phase is not proof of observed recovery, and accepted advisory prose is not verified causality or permission to change a business commitment. Preserve the observations and unresolved questions for the accountable owner.

## Infrastructure Notes

Use the scoped Ansible role and `docs/catalog-handoff.md`. Existing model Secret references are server-side. PH must approve learner binding, per-allocation model issuance/broker, immutable image distribution, runtime attributes and terminal integration. The engine is private; this path creates no public Route, learner pod shell or Secret-read grant. Automated dev qualification does not substitute for a human learner/catalog pilot or PH approval.
