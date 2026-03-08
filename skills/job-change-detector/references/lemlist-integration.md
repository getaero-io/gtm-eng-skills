# Lemlist Integration

## Create Campaign

```bash
CAMPAIGN_RESULT=$(deepline tools execute lemlist_create_campaign \
  --payload '{"name":"GTM Job Changers - March 2026"}' \
  --json)

CAMPAIGN_ID=$(echo "$CAMPAIGN_RESULT" | jq -r '.result.data.id')
SEQUENCE_ID=$(echo "$CAMPAIGN_RESULT" | jq -r '.result.data.sequence_id')

echo "Campaign: $CAMPAIGN_ID"
echo "Sequence: $SEQUENCE_ID"
```

## Add Sequence Steps

### Step 1: Initial Outreach

```bash
deepline tools execute lemlist_add_sequence_step --payload "{
  \"sequence_id\": \"$SEQUENCE_ID\",
  \"type\": \"email\",
  \"delay\": 0,
  \"subject\": \"Congrats on {{customFields.new_company}}\",
  \"message\": \"<p>Hi {{firstName}},</p>
<p>Saw you recently joined {{customFields.new_company}} as {{customFields.new_title}} - congrats!</p>
<p>I work with GTM leaders who are scaling their go-to-market operations. Given your background in {{customFields.area}}, I thought you might be interested in how we're helping teams like yours.</p>
<p>Would you be open to a quick chat?</p>
<p>Best,<br>[Your Name]</p>\",
  \"index\": 0
}"
```

### Step 2: Follow-up (Day 3)

```bash
deepline tools execute lemlist_add_sequence_step --payload "{
  \"sequence_id\": \"$SEQUENCE_ID\",
  \"type\": \"email\",
  \"delay\": 3,
  \"subject\": \"Quick thought on {{customFields.new_company}}\",
  \"message\": \"<p>{{firstName}},</p>
<p>Quick follow-up - given your focus on {{customFields.area}} at {{customFields.new_company}}, thought this might be relevant.</p>
<p>Happy to share how other GTM teams are solving similar challenges. 15 min call?</p>
<p>Best,<br>[Your Name]</p>\",
  \"index\": 1
}"
```

### Step 3: Final Touch (Day 7)

```bash
deepline tools execute lemlist_add_sequence_step --payload "{
  \"sequence_id\": \"$SEQUENCE_ID\",
  \"type\": \"email\",
  \"delay\": 7,
  \"subject\": \"Re: Congrats on {{customFields.new_company}}\",
  \"message\": \"<p>{{firstName}},</p>
<p>Last note - know the first few months in a new role are busy. If you'd like to see how {{customFields.similar_company}} improved their GTM efficiency by 40%, happy to share.</p>
<p>Let me know.</p>
<p>Best,<br>[Your Name]</p>\",
  \"index\": 2
}"
```

## Add Contacts to Campaign

```bash
deepline tools execute lemlist_add_to_campaign --payload "{
  \"campaign_id\": \"$CAMPAIGN_ID\",
  \"contacts\": [
    {
      \"email\": \"fabien.david@circleback.ai\",
      \"firstName\": \"Fabien\",
      \"lastName\": \"David\",
      \"company\": \"Circleback\",
      \"linkedin_url\": \"https://www.linkedin.com/in/fabiendavid\",
      \"custom_fields\": {
        \"new_company\": \"Circleback\",
        \"new_title\": \"Growth Advisor\",
        \"old_company\": \"Hex\",
        \"area\": \"growth marketing\",
        \"similar_company\": \"Notion, Airtable\"
      }
    },
    {
      \"email\": \"ybresler@ramp.com\",
      \"firstName\": \"Yuval\",
      \"lastName\": \"Bresler\",
      \"company\": \"Ramp\",
      \"linkedin_url\": \"https://www.linkedin.com/in/yuvalbresler\",
      \"custom_fields\": {
        \"new_company\": \"Ramp\",
        \"new_title\": \"Business Operations GTM AI\",
        \"old_company\": \"monday.com\",
        \"area\": \"GTM operations and AI\",
        \"similar_company\": \"Stripe, Brex\"
      }
    }
  ]
}"
```

## Custom Fields for Personalization

Recommended custom fields for job change campaigns:

- `new_company` - Where they just started
- `new_title` - Their new role
- `old_company` - Where they came from
- `area` - Their focus area (extracted from title/background)
- `similar_company` - Comparable companies for social proof

## Message Templates

### For "Moved" Status

Subject: `Congrats on {{customFields.new_company}}`

Body emphasizes:
1. Congratulate on new role
2. Reference their background/area of focus
3. Light value prop relevant to new company
4. Low-friction ask

### For "Left" Status (Open to Work)

Subject: `Exploring what's next?`

Body emphasizes:
1. Acknowledge transition period
2. Offer value/resources for job search
3. Connection, not pitch
4. Stay in touch

## Best Practices

- **Keep initial email under 100 words** - They're busy in new role
- **Personalize "area" field** - Map job title to focus area (e.g., "VP Growth" → "user acquisition and retention")
- **Use similar_company for social proof** - Pick 1-2 comparable companies in their industry
- **Wait 3-7 days between steps** - Give them time to settle in
- **Max 3 touch points** - Don't over-pursue
- **Add LinkedIn visit** - Optional step 1.5: LinkedIn profile visit (warming)

## Checking Campaign Stats

```bash
deepline tools execute lemlist_export_campaign_leads \
  --payload '{"campaign_id":"'$CAMPAIGN_ID'"}' \
  --json | jq '.result'
```

## Error Handling

Common Lemlist API errors:

- `502` - Upstream provider timeout, retry after 2-3 seconds
- `400` - Invalid email format or missing required field
- `409` - Contact already exists in campaign (not an error, skip)
