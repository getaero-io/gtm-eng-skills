# Searchbug Workflow Guidance

Use `searchbug_phone_validation` for US and Canadian phone numbers when you need connection status, line type, carrier, porting, or DNC/TCPA fields. It is a validation/compliance check, not a person-to-phone identity match.

The connector strips punctuation and a leading US/Canada country code before calling Searchbug's `api_lnp3` phone validator. The complete provider response is returned so newly added provider fields remain available without a Deepline release.

Use Trestle when you need activity scoring or identity matching, and use IPQS for fraud-risk screening after ordinary phone validation.
