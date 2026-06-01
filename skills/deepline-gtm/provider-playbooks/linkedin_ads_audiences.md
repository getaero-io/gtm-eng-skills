# LinkedIn Ads Audiences

Use these tools for LinkedIn Matched Audiences list-upload workflows.

- LinkedIn `LIST_UPLOAD` segments are replacement-oriented. Treat every sync as a refresh, not a true append.
- Choose `audience_kind: "contacts"` for hashed-email or people-match lists and `audience_kind: "companies"` for account lists.
- Contact lists work best at 10,000+ rows. Company lists work best at 1,000+ companies.
- After creating a list-upload segment, LinkedIn recommends a short delay before attaching the uploaded CSV.
- Monitor `destination_status` on the returned audience object and expect long processing times.
