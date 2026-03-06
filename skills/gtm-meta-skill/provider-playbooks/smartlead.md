Use Smartlead for outbound campaign writes after campaign discovery and field normalization.

- List campaigns first and choose a stable campaign id.
- Push leads using `smartlead_push_to_campaign` with Smartlead-style fields.
- Read stats with `smartlead_get_campaign_stats` after bulk pushes.
- Include `SMARTLEAD_API_KEY` as fallback env credential when not using org-linked auth.
- Use `smartlead_api_request` to reach any Smartlead API route not covered by dedicated actions.
- Keep payloads provider-native. There is no shared outbound standard contract for Smartlead.

```bash
deepline tools execute smartlead_list_campaigns --payload '{}'
```

```bash
deepline tools execute smartlead_push_to_campaign --payload '{"campaign_id":"12345678","leads":[{"email":"jane@example.com","first_name":"Jane","last_name":"Lovelace","company_name":"Acme Corp","custom_variables":{"tag":"demo"}}]}'
```

```bash
deepline tools execute smartlead_get_campaign_stats --payload '{"campaign_id":12345678}'
```

```bash
deepline tools execute smartlead_api_request --payload '{"method":"GET","endpoint":"/v1/campaigns"}'
```
