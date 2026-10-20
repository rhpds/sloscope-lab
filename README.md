# SLOscope lab

An RHDP Showroom lab for SREs and platform engineers making checkout reliability decisions with a service owner. This is the lab track, separate from AI Quickstarts work.

The core path starts with the checkout business decision, a short SLI/SLO/SLA primer, and event-flow/infrastructure diagrams before setup. Learners build a decision brief through Learn, Show, Do, Verify, and Takeaway sections: inspect synthetic telemetry, preserve a reference, measure controlled drift, exercise abstention, and review an export boundary. The core duration is estimated at 100 minutes, pending a learner pilot. The optional 20-minute MCP extension reviews inline artifacts through a real stdio client. Neither path establishes live model quality, alert behavior, or RHDP publication.

## Try the content

Use Python 3.11 and Git:

```bash
bash scripts/setup.sh
.lab/venv/bin/python scripts/check-exercises.py
```

Setup uses the immutable engine commit in `engine.lock.json` and its hashed requirements. The command checks use a temporary workspace and assert intended failures as well as successful results. They do not grade the business reasoning in the decision brief; the conclusion supplies a service-owner rubric for that review. They do not require model or cluster credentials.

For learner navigation, start at `content/modules/ROOT/pages/index.adoc`. `site.yml` builds the Antora site; `ui-config.yml` defines the terminal and OpenShift console tabs. Build with `npm ci && npm run build` after installing Node.js 22.

## Delivery status

Publishing House created this repository and started a **new, Classic, RHDP Published** workflow. Author content and infrastructure review remain pending. Engineering work is tracked in INTEL-83, related to INTEL-44; Publishing House onboarding is RHDPCD-2154. No stage transition or catalog publication is claimed here.

See `publishing-house/spec/design.md` for the proposed teaching design and `docs/delivery-contract.md` for unqualified infrastructure and live acceptance work. The Ansible example role fails explicitly while provisioning is unimplemented. Publishing House owns review and generation of the AgnosticV onboarding path.

## Sources and license

Engine: https://github.com/jkershawrh/slo-sli-automation. Scaffold: Publishing House Classic at `feb950bfc77ae28f3ccbfc096641c7d3c6d9d513`; Red Hat theme `v2.0.3` from that scaffold. Authoring uses the installed Showroom create-lab/common/verification guidance; no distinct local QS-to-lab skill was found.

New lab content and helpers are Apache-2.0; see LICENSE. Preserve upstream template and engine notices when redistributing.
