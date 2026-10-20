# Make checkout reliability decisions with SLOscope

## Overview

This hands-on SRE lab teaches how to give a service owner an evidence-backed checkout reliability recommendation. The fictional promotion review provides customer context without inventing revenue, conversion, or causal outcomes. A concise SLI/SLO/SLA primer and source-backed event-flow/infrastructure diagrams precede all setup. Each module follows Learn, Show, Do, Verify, and Takeaway and contributes to a reusable decision brief. Learners inspect synthetic service evidence, preserve a reference, compare a controlled change, reject insufficient or contradictory inputs, and test an SLO export boundary. An optional MCP extension exposes the same evidence review through a local stdio protocol.

The business scenario is fictional Example Retail reviewing checkout-service targets after an error-count change. The training comparison deliberately retains the original query window and edits the error count; it is a counterfactual fixture, not an independently collected later sample. The event-flow diagram distinguishes that from the live later-window path. No customer result, real-model quality, live alert behavior, or production target is claimed by the recorded exercises.

## Target Audience

- **Role:** SREs and platform engineers.
- **Experience level:** Intermediate.
- **Existing knowledge:** Shell commands, JSON, HTTP status codes, basic metrics, and SLO concepts.
- **Skills taught:** Reproducible evidence review, frozen references, abstention, numeric/identity boundaries, and separation of interpretation from operational authority.

## Prerequisites

Python 3.11, Git, writable per-user terminal workspace, the exact engine source lock, and its hashed dependencies. Setup requires public GitHub and Python package-index access unless pre-seeded. The core exercises need no model credential, monitoring permission, cluster login, or GPU. Provisioning and an independent regular-user walk-through remain pending. Local health checks verify imports and source identity rather than accepting an empty deployment.

## Learning Objectives

1. Explain SLI, SLO, and SLA, then trace the evidence flow and infrastructure boundaries before collecting or interpreting data.
2. Inspect service identity, telemetry window, reported coverage, and histogram vocabulary before interpretation.
3. Preserve a reference baseline and compare a controlled changed window without replacing it.
4. Demonstrate abstention for low coverage and contradictory measured signals.
5. Verify a histogram export boundary and distinguish an artifact preview from target approval or alert acceptance.
6. Optionally review inline artifacts through bounded MCP tools and verify a real stdio exchange.

## Content Type

Lab: hands-on workshop. This is the SLOscope RHDP lab track, not a new AI Quickstart publication.

## Products & Technologies

Proposed hosting: Red Hat OpenShift with RHDP Classic Showroom. Tested core terminal runtime: Python 3.11; source and dependency references are locked in the repository. Upstream components: SLOscope, Prometheus/OpenSLO preview artifacts, Antora, and optional MCP Python SDK 2.3.0. OpenShift release and live model remain pending infrastructure review; no tested cluster version is claimed.

## Module Map

1. Business assignment, reliability primer, event-flow and infrastructure architecture, and setup: 15 minutes, author estimate.
2. Inspect evidence and freeze a reference: 20 minutes, hands-on.
3. Measure drift and practice abstention: 30 minutes, hands-on plus review questions.
4. Review targets and export safely: 25 minutes, hands-on.
5. Review, cleanup, and next steps: 10 minutes.
6. Optional MCP extension: 20 minutes, real stdio integration against synthetic artifacts.

Core total: 100 minutes. With MCP: 120 minutes. Estimates are for pacing and remain subject to independent learner timing.

## Difficulty Level

Intermediate.

## Environment

**Learner view:** A Classic Showroom with terminal and Red Hat OpenShift console tabs. The terminal has an isolated writable workspace. Core exercises run against public synthetic artifacts, not a connected production telemetry endpoint. The implementation preserves synthetic provenance and labels recorded model demonstrations explicitly.

**Automation needed:** Yes. Provision and pre-seed Python 3.11, Git, locked source/dependencies, learner workspace, runtime attributes, and cleanup. Live extension automation additionally needs a controlled sample service, monitored labels/windows, real read access to metrics, supported model access, scoped secrets, artifact storage, and API access controls.

The generated Ansible example intentionally fails until provisioning is implemented. QA playbooks verify an existing terminal/source contract and complete deterministic command sequence. They do not provision infrastructure or establish live acceptance.

## Infrastructure Requirements

- **Proposed platform:** Red Hat OpenShift; release is pending review and supplied at runtime through attributes.
- **Cloud provider:** CNV is the template default, not a validated sizing decision.
- **Cluster type/topology/sizing/concurrency:** Pending infrastructure review; do not infer requirements from the local synthetic run.
- **Automation:** Ansible through Publishing House. AgnosticV generation and catalog onboarding remain owned by the PH workflow.
- **Core AI requirement:** None; recorded/synthetic core exercises do not call a model.
- **Live AI extension:** Supported open-weight model via an approved endpoint; model identity, access, and sizing remain pending. No dedicated GPU requirement is established.
- **External services:** Public GitHub, Python package indexes, Node package registry, and theme release download at setup/build. Approved pre-seeding is preferred for final delivery. Live telemetry and model endpoints need separate ownership review.
- **Security/storage:** Scoped learner identity, verified TLS, server-side model secrets, namespace/metric isolation, OAuth/API controls, writable artifact PVC/permissions, and explicit cleanup require implementation and acceptance.
- **Non-GA products:** No non-GA product dependency established; reviewers must classify any chosen live model/serving stack before acceptance.

## Assessment Strategy

Every task module teaches the concept before commands, uses a worked example and learner prediction/choice, and includes technical and owner-facing verification. Learners build a decision brief with Evidence basis, Reliability assessment, and Target and release recommendation sections. The conclusion uses an explicit review rubric; automated checks do not claim to grade business reasoning. A reusable template is in content/modules/ROOT/attachments/decision-brief.md. `scripts/check-exercises.py` executes the same helper sequence in a disposable directory and asserts exact exit codes/reasons for reference replacement, coverage, contradictory breach lists, missing histogram thresholds, and live-without-model behavior. It also corrupts a reference to verify the final checkpoint fails. The optional MCP check uses a real SDK client/server session and asserts tool boundaries plus admissibility/abstention.

These tests establish local synthetic behavior. Remaining acceptance is listed in `docs/delivery-contract.md`: independent rendered learner completion, real telemetry/model behavior, alert firing/recovery/missing data, consumer validation, regular-user installation/security, immutable image qualification, RCARS/content/infrastructure review, and RHDP publication. No workflow approval or stage is edited by this PR.

## Learner walkthrough corrections

A clean default clone exposed that main still contains only the PH scaffold. Review instructions now select the actual draft content branch, with immutable published content still a gate. Learner pages teach p99/cumulative buckets before use, show a worked drift row and the actual availability_drop dominant label, contrast the recorded proposal with this baseline, and expose real MCP response summaries/digests. Literal core page commands run in CI in addition to helper-only checks; clean builds remove renamed stale pages. These checks support, but do not grade, the owner-facing decision brief.
