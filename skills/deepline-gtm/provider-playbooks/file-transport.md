# File transport

This is an internal transport seam for turning bounded, in-memory-safe data into
provider upload bytes. It is not an agent-callable integration tool.

- Use a bounded materializer for Dataset Handles; never load an entire dataset
  before applying row, column, and byte limits.
- Preserve and return the materializer's transport report so callers can tell
  users when an export was truncated.
- Treat an incomplete source read as a partial result, not a successful full
  export. Callers decide whether that partial result is acceptable for their
  provider contract.
- Keep provider-specific limits and upload protocol handling in the provider
  action. This module owns safe data materialization, not provider policy.
