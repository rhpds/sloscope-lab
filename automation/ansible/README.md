# Infrastructure automation status

This is the Publishing House Ansible scaffold. Infrastructure provisioning is not implemented or qualified by this content PR. The example role intentionally fails instead of reporting a successful empty deployment.

Review `docs/delivery-contract.md` for the required terminal, per-user resources, telemetry, model, storage, permission, and cleanup contracts. The executable `qa-automation/` checks verify an already provisioned terminal and synthetic exercise sequence; they do not provision a cluster or certify the live path.
