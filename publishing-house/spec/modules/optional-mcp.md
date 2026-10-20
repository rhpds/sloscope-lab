# Review artifacts through MCP

## Brief Overview

Review artifacts through MCP in the fictional Example Retail review, using synthetic artifacts and explicit acceptance boundaries.

## Audience and Time

Intermediate SRE/platform engineers; 20 minutes. Complete the preceding core pages first.

## Learning Objectives

- Inspect immutable optional source and read-only tool inputs.
- Run a real stdio client and server with inline artifacts.

## Lab Structure

Use the detailed guided content at `content/modules/ROOT/pages/06-mcp.adoc`.

## Detailed Steps

1. Inspect immutable optional source and read-only tool inputs.
2. Run a real stdio client and server with inline artifacts.
3. Verify admissible and insufficient-evidence outcomes.

## Key Takeaways

Evidence acceptance and rendered/protocol success do not establish live-model quality, deployed alert behavior, or operational approval.

## Infrastructure Notes

Core path is terminal-only against locked engine code. Optional MCP has its own pinned source/environment. Live and RHDP gates remain in docs/delivery-contract.md.
