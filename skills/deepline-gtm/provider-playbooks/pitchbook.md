PitchBook actions use only the workspace's own PitchBook API key. The key needs
an API contract with access to the requested endpoint and sufficient PitchBook
credits. PitchBook charges that account; Deepline does not bill for these calls.

Start with a search action to obtain a PitchBook `pbId`, then use the matching
entity action for details. Bulk POST actions retrieve multiple records and also
spend PitchBook credits. Check the customer's contract before using endpoints
outside their licensed areas. A 402 response means insufficient PitchBook
credits; a 403 can mean the endpoint is not licensed.
