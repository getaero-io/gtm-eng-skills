# Examples

## Example 1: Find GTM Contacts Who Changed Jobs (Last 6 Months)

**User request**: "Find GTM contacts who changed jobs in the last 6 months and add them to a Lemlist campaign"

**Execution**:

```bash
cd /tmp/job-change
export HUBSPOT_API_KEY="pat-na2-..."

# 1. Query HubSpot for GTM contacts
cat > search.json <<'EOF'
{
  "filterGroups": [
    {"filters": [{"propertyName": "jobtitle", "operator": "CONTAINS_TOKEN", "value": "GTM"}]},
    {"filters": [{"propertyName": "jobtitle", "operator": "CONTAINS_TOKEN", "value": "Growth"}]}
  ],
  "properties": ["email", "firstname", "lastname", "jobtitle", "company", "hs_linkedin_url"],
  "limit": 50
}
EOF

curl -s -X POST "https://api.hubapi.com/crm/v3/objects/contacts/search" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d @search.json | python3 -c "..." > contacts.csv

# 2. Extract domain + check job changes
cat > extract_domain.js <<'EOF'
const email = row.email;
return email && email.includes('@') ? email.split('@')[1] : '';
EOF

deepline enrich --csv contacts.csv --output step1.csv \
  --with 'domain=run_javascript:@extract_domain.js'

deepline enrich --csv step1.csv --in-place --rows 0:1 \
  --with 'job_change=deepline_native_job_change:{"company_domain":"{{domain}}","professional_email":"{{email}}","contact_linkedin":"{{linkedin_url}}","contact_full_name":"{{firstname}} {{lastname}}"}'

# User approves, run full
deepline enrich --csv step1.csv --in-place \
  --with 'job_change=deepline_native_job_change:...'

# 3. Parse status
cat > parse_status.js <<'EOF'
const jc = row.job_change;
return jc?.data?.output?.job_change_status || '';
EOF

deepline enrich --csv step1.csv --in-place \
  --with 'status=run_javascript:@parse_status.js'

# 4. Filter for job changers
python3 filter_job_changers.py  # Creates job_changers.csv

# 5. Find new emails (for "moved" contacts)
deepline enrich --csv job_changers.csv --output final.csv \
  --with 'new_email=dropleads_email_finder:{"first_name":"{{firstname}}","last_name":"{{lastname}}","company_domain":"{{new_domain}}"}'

# 6. Create Lemlist campaign and add contacts
# (See lemlist-integration.md for full details)
```

**Result**: 3 job changers identified, added to Lemlist campaign with personalized sequences

---

## Example 2: Update HubSpot CRM After Job Changes

**User request**: "Update the CRM with the new company information"

**Execution**:

```bash
# For each job changer, update HubSpot

CONTACT_ID="438245457605"
NEW_COMPANY="Ramp"
NEW_DOMAIN="ramp.com"
NEW_TITLE="Business Operations GTM AI"

# 1. Update job title + job change date
curl -X PATCH "https://api.hubapi.com/crm/v3/objects/contacts/$CONTACT_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"properties\": {
      \"jobtitle\": \"$NEW_TITLE\",
      \"hs_job_change_detected_date\": \"$(date +%Y-%m-%d)\"
    }
  }"

# 2. Find Ramp company record
COMPANY_ID=$(curl -s -X POST "https://api.hubapi.com/crm/v3/objects/companies/search" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filterGroups":[{"filters":[{"propertyName":"name","operator":"EQ","value":"Ramp"}]}]}' \
  | jq -r '.results[0].id')

# 3. Get old company association
OLD_COMPANY_ID=$(curl -s "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  | jq -r '.results[] | select(.associationTypes[].typeId == 1) | .toObjectId')

# 4. Remove old association
curl -X DELETE "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies/$OLD_COMPANY_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY"

# 5. Add new association
curl -X PUT "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies/$COMPANY_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{"associationCategory":"HUBSPOT_DEFINED","associationTypeId":1}]'
```

**Result**: Contact now shows Ramp as primary company in HubSpot CRM

---

## Example 3: Job Change Detection Only (No Campaign)

**User request**: "Which of my contacts changed jobs recently?"

**Simplified execution** (no email finding, no campaign):

```bash
# Steps 1-3 from Example 1, then:

# Filter and report
python3 <<'EOF'
import csv, json

with open('step1.csv', 'r') as f:
    reader = csv.DictReader(f)
    print("Job Changers:")
    print("-" * 80)

    for row in reader:
        if row.get('status') in ['moved', 'left']:
            jc = json.loads(row['job_change'])
            person = jc['data']['output']['person']

            old_company = row.get('domain', '').split('.')[0]
            new_company = person.get('company_name', 'None')
            title = person.get('title', '')

            print(f"{row['firstname']} {row['lastname']}")
            print(f"  {old_company} → {new_company}")
            print(f"  New role: {title}")
            print(f"  Status: {row['status']}")
            print()
EOF
```

**Output**:
```
Job Changers:
--------------------------------------------------------------------------------
Fabien David
  hex → Circleback
  New role: Growth Advisor
  Status: moved

Yuval Bresler
  yotpo → Ramp
  New role: Business Operations GTM AI
  Status: moved

Noah Yoseloff
  owner → None
  New role: Growth Marketer
  Status: left
```
