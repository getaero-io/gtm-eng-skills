# Versium

Use Versium for US consumer and business enrichment. If the workspace connects
its own API key, that key takes precedence and Deepline does not bill the
provider usage. Otherwise, actions with complete match-credit pricing use
Deepline-managed access. Contact Append and Predictive Scores still require a
workspace key because the supplied pricing table does not fully price them.

Choose the narrowest action and output set that answers the request. Contact,
demographic, audience, and predictive-score actions require at least one person
identifier. Firmographic append requires a company identifier. Treat hashed
email input as sensitive data even though it is not plaintext.
