# Review targets and export safely

## Brief Overview

Review targets and export safely in the fictional Example Retail review, using synthetic artifacts and explicit acceptance boundaries.

## Audience and Time

Intermediate SRE/platform engineers; 25 minutes. Complete the preceding core pages first.

## Learning Objectives

- Reject recorded 595 ms threshold absent from measured histogram.
- Render a manually edited 1000 ms preview and explain its limited meaning.

## Lab Structure

Use the detailed guided content at `content/modules/ROOT/pages/05-review-and-export.adoc`.

## Detailed Steps

1. Reject recorded 595 ms threshold absent from measured histogram.
2. Render a manually edited 1000 ms preview and explain its limited meaning.
3. Verify default-live failure and explicitly labeled fixture response.

## Key Takeaways

Evidence acceptance and rendered/protocol success do not establish live-model quality, deployed alert behavior, or operational approval.

## Infrastructure Notes

Core path is terminal-only against locked engine code. Optional MCP has its own pinned source/environment. Live and RHDP gates remain in docs/delivery-contract.md.
