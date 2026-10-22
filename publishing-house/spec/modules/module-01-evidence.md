# Inspect evidence and freeze a reference

## Brief Overview

Inspect evidence and freeze a reference in the fictional Example Retail review, using synthetic artifacts and explicit acceptance boundaries.

## Audience and Time

Intermediate SRE/platform engineers; 20 minutes. Complete the preceding core pages first.

## Learning Objectives

- Inspect service identity, reported coverage, counts, and histogram boundaries.
- Compute the baseline and preserve its hash.

## Lab Structure

Use the detailed guided content at `content/modules/ROOT/pages/03-evidence-and-reference.adoc`.

## Detailed Steps

1. Inspect service identity, reported coverage, counts, and histogram boundaries.
2. Compute the baseline and preserve its hash.
3. Confirm a second baseline command refuses replacement.

## Key Takeaways

Evidence acceptance and rendered/protocol success do not establish live-model quality, deployed alert behavior, or operational approval.

## Infrastructure Notes

Core path is terminal-only against locked engine code. Optional MCP has its own pinned source/environment. Live and RHDP gates remain in docs/delivery-contract.md.

## Learning design and business handoff

Teach the concept and decision stakes before commands; use a worked example, learner prediction/choice, technical verification, and owner-facing takeaway. Contribute the matching section to the downloadable decision brief. The technical checker does not grade business reasoning. Introduce SLI/SLO/SLA and the event-flow/infrastructure architecture before setup, using the shared 02-how-it-works page.
