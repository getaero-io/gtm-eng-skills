# CrustData V2 Guidance

CrustData V2 is hidden from tool discovery: CrustData no longer serves Deepline's V2 API access, so every V2 call fails with a provider authorization error. Use the `crustdata_v3_*` tools for new workflows and migrate existing ones; confirm each V3 schema with `deepline describe <tool-id>`, since V3 uses its own filter vocabulary, not a renamed V2 payload.

Do not expose provider credit ladders to customers; Deepline tool pricing should remain Deepline-facing.
