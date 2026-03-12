Use Smartlead for outbound campaign writes after campaign discovery and field normalization.

- List campaigns first and choose a stable campaign id.
- Create campaigns with `smartlead_create_campaign`.
- Push leads using `smartlead_push_to_campaign` with Smartlead-style fields.
- Read stats with `smartlead_get_campaign_stats` after bulk pushes.
- Include `SMARTLEAD_API_KEY` as fallback env credential when not using org-linked auth.
- Keep payloads provider-native. There is no shared outbound standard contract for Smartlead.

```bash
deepline tools execute smartlead_list_campaigns --payload '{}'
```

```bash
deepline tools execute smartlead_create_campaign --payload '{"name":"Insurance Brokerage - Book Assessment"}'
```

```bash
deepline tools execute smartlead_push_to_campaign --payload '{"campaign_id":"12345678","leads":[{"email":"jane@example.com","first_name":"Jane","last_name":"Lovelace","company_name":"Acme Corp","custom_fields":{"tag":"demo"}}]}'
```

```bash
deepline tools execute smartlead_get_campaign_stats --payload '{"campaign_id":12345678}'
```
