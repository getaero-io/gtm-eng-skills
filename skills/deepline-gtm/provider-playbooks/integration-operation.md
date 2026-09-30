# Integration Operation

Use this module to create, execute, fence, persist, and present a durable provider invocation as one retry-safe Integration Operation.

- Keep provider-specific input parsing, credentials, and HTTP transport at the caller boundary.
- Persist the operation intent and external identity before an external side effect; retries must resume the same operation rather than create another charge or resource.
- Use the gateway adapters for canonical outcome reads and transitions. Keep legacy response shaping behind the presentation alias during the compatibility window.
- Treat a provider outcome as ambiguous unless its documented contract proves completion, deletion, or absence.
