---
name: job-change-detector
description: >
  Detect which HubSpot CRM contacts have changed jobs in the last 6 months using Deepline's
  job change API. Filter by job title/role, find new work emails, and add to outbound campaigns
  with personalized sequences. Uses deepline_native_job_change API + HubSpot API for CRM updates
  + optional Lemlist/outbound integration.

  Use when asked to: "find GTM contacts who changed jobs", "detect recent job changes in HubSpot",
  "find job changers and add to campaign", "who moved to new companies", "employment changes in CRM",
  "get new emails for job changers".
---

# Job Change Detector

**Requires**: Deepline CLI + HubSpot API key

Detects recent job changes (default: last 6 months) for filtered HubSpot contacts, finds their new
work emails, and optionally adds them to outbound campaigns.

## Quick Start

```bash
# Setup
mkdir -p /tmp/job-change && cd /tmp/job-change
deepline backend start

# Get HubSpot API key
export HUBSPOT_API_KEY="pat-na2-..."  # From ~/.env.local or user
```

## Core Workflow

### Step 1: Query HubSpot for Target Contacts

Use HubSpot Search API to filter contacts by job title/role:

```bash
# Create search payload (adjust filters for GTM, engineering, etc.)
cat > hubspot_search.json <<'EOF'
{
  "filterGroups": [
    {"filters": [{"propertyName": "jobtitle", "operator": "CONTAINS_TOKEN", "value": "GTM"}]},
    {"filters": [{"propertyName": "jobtitle", "operator": "CONTAINS_TOKEN", "value": "Growth"}]},
    {"filters": [{"propertyName": "jobtitle", "operator": "CONTAINS_TOKEN", "value": "Revenue Operations"}]}
  ],
  "properties": ["email", "firstname", "lastname", "jobtitle", "company", "hs_linkedin_url"],
  "limit": 50
}
EOF

# Query HubSpot and create CSV
curl -s -X POST "https://api.hubapi.com/crm/v3/objects/contacts/search" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d @hubspot_search.json \
  | python3 -c "
import json, sys, csv
data = json.load(sys.stdin)
writer = csv.writer(sys.stdout)
writer.writerow(['hubspot_id','email','firstname','lastname','jobtitle','company','linkedin_url'])
for r in data.get('results', []):
    p = r['properties']
    writer.writerow([r['id'], p.get('email',''), p.get('firstname',''),
                     p.get('lastname',''), p.get('jobtitle',''),
                     p.get('company',''), p.get('hs_linkedin_url','')])
" > raw_contacts.csv
```

### Step 2: Extract Domain + Check Job Changes

**Key pattern**: deepline_native_job_change requires `company_domain`, but HubSpot's `company`
field is often a name, not domain. Extract domain from email when company field is empty.

```bash
# Create domain extraction script
cat > extract_domain.js <<'EOF'
const email = row.email;
return email && email.includes('@') ? email.split('@')[1] : '';
EOF

# Add domain column
deepline enrich --csv raw_contacts.csv \
  --output with_domain.csv \
  --with 'domain=run_javascript:@extract_domain.js'

# Run job change detection (pilot first)
deepline enrich --csv with_domain.csv \
  --in-place \
  --rows 0:2 \
  --with 'job_change=deepline_native_job_change:{"company_domain":"{{domain}}","professional_email":"{{email}}","contact_linkedin":"{{linkedin_url}}","contact_full_name":"{{firstname}} {{lastname}}"}'
```

**Approval**: Show pilot results, get user approval for full run.

```bash
# Full run after approval
deepline enrich --csv with_domain.csv \
  --in-place \
  --with 'job_change=deepline_native_job_change:{"company_domain":"{{domain}}","professional_email":"{{email}}","contact_linkedin":"{{linkedin_url}}","contact_full_name":"{{firstname}} {{lastname}}"}'
```

### Step 3: Parse Job Change Status

```bash
cat > parse_status.js <<'EOF'
const jc = row.job_change;
if (!jc || !jc.data || !jc.data.output) return '';
return jc.data.output.job_change_status || '';
EOF

deepline enrich --csv with_domain.csv \
  --in-place \
  --with 'status=run_javascript:@parse_status.js'
```

### Step 4: Filter for Job Changers

```bash
# Extract contacts with "moved" or "left" status
python3 <<'EOF'
import csv, json

with open('with_domain.csv', 'r') as f:
    reader = csv.DictReader(f)
    with open('job_changers.csv', 'w') as out:
        writer = csv.DictWriter(out, fieldnames=['firstname','lastname','old_email','new_company','new_title','linkedin_url','status'])
        writer.writeheader()

        for row in reader:
            status = row.get('status', '')
            if status in ['left', 'moved']:
                jc = json.loads(row['job_change']) if row.get('job_change') else {}
                person = jc.get('data', {}).get('output', {}).get('person', {})

                writer.writerow({
                    'firstname': row['firstname'],
                    'lastname': row['lastname'],
                    'old_email': row['email'],
                    'new_company': person.get('company_name', ''),
                    'new_title': person.get('title', ''),
                    'linkedin_url': row['linkedin_url'],
                    'status': status
                })
EOF
```

### Step 5: Find New Work Emails

For contacts who "moved" (not "left"), find their new work emails:

```bash
# Add new_domain column (infer from new_company)
# Then use dropleads_email_finder or hunter_email_finder
deepline enrich --csv job_changers.csv \
  --output with_new_emails.csv \
  --with 'new_email=dropleads_email_finder:{"first_name":"{{firstname}}","last_name":"{{lastname}}","company_domain":"{{new_domain}}"}'
```

### Step 6: Update HubSpot CRM

**CRITICAL**: HubSpot uses **Company record associations**, not text fields.

```bash
# Update contact properties (job title, job change date)
curl -X PATCH "https://api.hubapi.com/crm/v3/objects/contacts/$CONTACT_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"properties\": {
      \"jobtitle\": \"$NEW_TITLE\",
      \"hs_job_change_detected_date\": \"$(date +%Y-%m-%d)\"
    }
  }"

# Find or create new Company record
COMPANY_ID=$(curl -s -X POST "https://api.hubapi.com/crm/v3/objects/companies/search" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"filterGroups\":[{\"filters\":[{\"propertyName\":\"name\",\"operator\":\"EQ\",\"value\":\"$NEW_COMPANY\"}]}]}" \
  | jq -r '.results[0].id // empty')

if [ -z "$COMPANY_ID" ]; then
  COMPANY_ID=$(curl -s -X POST "https://api.hubapi.com/crm/v3/objects/companies" \
    -H "Authorization: Bearer $HUBSPOT_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"properties\":{\"name\":\"$NEW_COMPANY\",\"domain\":\"$NEW_DOMAIN\"}}" \
    | jq -r '.id')
fi

# Remove old company association, add new one
curl -X DELETE "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies/$OLD_COMPANY_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY"

curl -X PUT "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies/$COMPANY_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{"associationCategory":"HUBSPOT_DEFINED","associationTypeId":1}]'
```

See [references/hubspot-api.md](references/hubspot-api.md) for full CRM update patterns.

### Step 7: Add to Outbound Campaign (Optional)

```bash
# Create Lemlist campaign
CAMPAIGN_ID=$(deepline tools execute lemlist_create_campaign \
  --payload '{"name":"GTM Job Changers - March 2026"}' \
  --json | jq -r '.result.data.id')

# Add contacts with custom fields for personalization
deepline tools execute lemlist_add_to_campaign --payload "{
  \"campaign_id\": \"$CAMPAIGN_ID\",
  \"contacts\": [
    {
      \"email\": \"$NEW_EMAIL\",
      \"firstName\": \"$FIRSTNAME\",
      \"lastName\": \"$LASTNAME\",
      \"company\": \"$NEW_COMPANY\",
      \"custom_fields\": {
        \"new_company\": \"$NEW_COMPANY\",
        \"new_title\": \"$NEW_TITLE\",
        \"old_company\": \"$OLD_COMPANY\"
      }
    }
  ]
}"
```

See [references/lemlist-integration.md](references/lemlist-integration.md) for sequence templates.

## Job Change Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `moved` | At new company (has current_position) | Find new email, add to campaign |
| `left` | Left old company, no new position | Use old email, note "open to work" |
| `no_change` | Still at same company | Skip |
| `unknown` | Could not determine | Skip |

## Common Patterns

### Filter by Time Window

Default is 6 months. To filter to specific window:

```bash
# Filter job changes to last 3 months
python3 <<'EOF'
import csv, json
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=90)

with open('with_domain.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('status') in ['moved', 'left']:
            jc = json.loads(row['job_change'])
            person = jc.get('data', {}).get('output', {}).get('person', {})
            experiences = person.get('experiences', [])
            if experiences:
                end_date = experiences[0].get('end_date')
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    if end_dt >= cutoff:
                        print(f"{row['email']}: Changed job on {end_date}")
EOF
```

### Multi-Step Enrich Pattern

When deepline enrich needs intermediate columns (like `domain` before `job_change`):

```bash
# Step 1: Add domain
deepline enrich --csv input.csv --output step1.csv \
  --with 'domain=run_javascript:@extract_domain.js'

# Step 2: Use domain in next column
deepline enrich --csv step1.csv --in-place \
  --with 'job_change=deepline_native_job_change:{"company_domain":"{{domain}}",...}'
```

## Troubleshooting

**Error: "Bad request" from deepline_native_job_change**
- Cause: `company_domain` is empty or invalid (company name instead of domain)
- Fix: Use domain extraction pattern from Step 2

**HubSpot profile shows old company after update**
- Cause: Updated text field, not Company association
- Fix: Follow Step 6 pattern to update Company associations

**High "unknown" status rate**
- Cause: Contacts missing LinkedIn URLs
- Fix: Run LinkedIn resolution first (see linkedin-url-lookup skill)

## Cost Estimates

- `deepline_native_job_change`: 2 credits per contact (only charges on "moved" status)
- `dropleads_email_finder`: 0.3 credits per contact
- Total for 100 contacts: ~200-250 credits (assuming 20% job change rate)

## References

- [references/hubspot-api.md](references/hubspot-api.md) - HubSpot API patterns for CRM updates
- [references/lemlist-integration.md](references/lemlist-integration.md) - Campaign setup + sequence templates
- [references/examples.md](references/examples.md) - End-to-end examples with real data
