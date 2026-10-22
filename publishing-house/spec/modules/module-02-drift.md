# Measure drift and practice abstention

## Brief Overview

Measure drift and practice abstention in the fictional Example Retail review, using synthetic artifacts and explicit acceptance boundaries.

## Audience and Time

Intermediate SRE/platform engineers; 30 minutes. Complete the preceding core pages first.

## Learning Objectives

- Compare edited synthetic error counts with the preserved reference.
- Inspect input digest and measured breached indicators.

## Lab Structure

Use the detailed guided content at `content/modules/ROOT/pages/04-drift-and-abstention.adoc`.

## Detailed Steps

1. Compare edited synthetic error counts with the preserved reference.
2. Inspect input digest and measured breached indicators.
3. Verify exact low-coverage and conflicting-list abstentions.

## Key Takeaways

Evidence acceptance and rendered/protocol success do not establish live-model quality, deployed alert behavior, or operational approval.

## Infrastructure Notes

Core path is terminal-only against locked engine code. Optional MCP has its own pinned source/environment. Live and RHDP gates remain in docs/delivery-contract.md.

## Learning design and business handoff

Teach the concept and decision stakes before commands; use a worked example, learner prediction/choice, technical verification, and owner-facing takeaway. Contribute the matching section to the downloadable decision brief. The technical checker does not grade business reasoning. Introduce SLI/SLO/SLA and the event-flow/infrastructure architecture before setup, using the shared 02-how-it-works page.
