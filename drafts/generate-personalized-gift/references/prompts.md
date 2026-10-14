# The four AI steps — prompts, models and outputs

These are the author's prompts, **verbatim**. The only edits: each column reference in the original (Clay) build became a
`{{variable}}`, and the gift budget in *Ideate Gift* became `{{gift_budget}}` so the installer can set it.
**Do not reword, shorten or merge them.** Every variable is interpolated into its step's prompt from
the step named in the table under it.

Each model maps to the exact AI Gateway id passed as `deeplineagent`'s `model`: `claude-sonnet-5` →
`anthropic/claude-sonnet-5`, `gpt-4.1-mini` → `openai/gpt-4.1-mini` (both listed at
https://ai-gateway.vercel.sh/v1/models on 2026-09-30). If a listed model is not available, **say so
and ask which to use** — never substitute one silently.

## 1. Research Interests

- **Model:** `claude-sonnet-5`
- **Output fields:** `interests`, `research_notes`

| Variable | Wired from |
|---|---|
| `{{company}}` | Enrich person → current employer name |
| `{{full_name}}` | Enrich person → `full_name` |
| `{{job_title}}` | Enrich person → `title` |
| `{{linkedin_url}}` | the input row's `linkedin_url` |

```text
You are a thoughtful gift researcher. Your job is to figure out what {{full_name}}  — who works as {{job_title}} at {{company}} — is genuinely interested in, so we can pick a meaningful gift.
Here is what we already know:
Name: {{full_name}}
Title: {{job_title}}
Company: {{company}}
LinkedIn: {{linkedin_url}}

Use your web/browsing tools to research their public social presence — LinkedIn posts and bio, and any other public activity you can find (Twitter/X, GitHub, personal site, press). Look for signals of genuine personal interests, hobbies, passions, causes, or tastes (not just job skills). Examples: a sport they play, a cause they support, a hobby, a favorite author/genre, coffee/tea obsession, gaming, running, cooking, travel, pets, music, etc.
If web tools are unavailable, reason carefully from the known title, company, skills, and background to infer the most likely genuine interests, and note that these are inferred.
Return:
interests: a concise list (comma-separated) of their 2-4 strongest, most specific interests
research_notes: 2-3 sentences citing the concrete evidence you found (which post/profile/repo) or, if inferred, your reasoning.
```

## 2. Ideate Gift

- **Model:** `gpt-4.1-mini`
- **Output fields:** `gift_idea`, `search_query`, `gift_rationale`

| Variable | Wired from |
|---|---|
| `{{company}}` | Enrich person → current employer name |
| `{{full_name}}` | Enrich person → `full_name` |
| `{{gift_budget}}` | the declared **Gift budget** input (default `$30-$150`) |
| `{{interests}}` | Research Interests → `interests` |
| `{{job_title}}` | Enrich person → `title` |
| `{{research_notes}}` | Research Interests → `research_notes` |

```text
You are a tasteful gift curator. Based on the research below, propose ONE specific, fitting gift for {{full_name}} ({{job_title}} at {{company}}).
Their interests: {{interests}} Research notes: {{research_notes}}
Rules for a great gift:
Specific and real (a concrete product type/brand, not \"a book\" but e.g. \"the Fellow Stagg EKG electric kettle\" for a coffee enthusiast).
Thoughtful and tied directly to a genuine interest — it should feel personal, not generic swag.
Reasonably giftable in a professional context (roughly {{gift_budget}}, tasteful, nothing too personal or intimate).
Something purchasable online with a clear product page.
Return:
gift_idea: the specific gift (include brand/model if relevant)
gift_rationale: one sentence on why it fits this person's interest
search_query: a precise web-search query that would find this exact product to buy (e.g. \"Fellow Stagg EKG electric pour-over kettle buy\").
```

## 3. Purchasable Product Link

- **Model:** `gpt-4.1-mini`
- **Output fields:** `price`, `product_url`, `product_name`, `link_verified`

| Variable | Wired from |
|---|---|
| `{{gift_idea}}` | Ideate Gift → `gift_idea` |
| `{{gift_rationale}}` | Ideate Gift → `gift_rationale` |
| `{{search_query}}` | Ideate Gift → `search_query` |

```text
Find a real, purchasable product page for this gift so it can be sent in a message.
Gift: {{gift_idea}} 
Why it fits: {{gift_rationale}} 
Search query to use: {{search_query}}
Use your web/search tools to find a specific, live product page where this exact item can be bought (prefer the brand's own site or a major reputable retailer like Amazon; avoid dead links, marketplaces with sketchy listings, or generic category pages). Verify the link points to the actual product.
If web tools are unavailable, return the most likely canonical retailer URL you are confident about and set link_verified to false.
Return:
product_name: the exact product title as listed
product_url: a direct link to buy it
price: approximate price with currency (e.g. \"$149\")
link_verified: \"true\" if you confirmed the page via a tool, otherwise \"false\".
```

## 4. Personalized Message Gen

- **Model:** `claude-sonnet-5`
- **Output fields:** `price`, `title`, `company`, `full_name`, `gift_idea`, `interests`, `product_url`, `product_name`, `personalized_message`

| Variable | Wired from |
|---|---|
| `{{company}}` | Enrich person → current employer name |
| `{{full_name}}` | Enrich person → `full_name` |
| `{{gift_idea}}` | Ideate Gift → `gift_idea` |
| `{{gift_rationale}}` | Ideate Gift → `gift_rationale` |
| `{{interests}}` | Research Interests → `interests` |
| `{{job_title}}` | Enrich person → `title` |
| `{{price}}` | Purchasable Product Link → `price` |
| `{{product_name}}` | Purchasable Product Link → `product_name` |
| `{{product_url}}` | Purchasable Product Link → `product_url` |

```text
Write a short, warm, personalized message to send in a thread alongside a gift for {{full_name}} ({{job_title}} at {{company}}).
Context:
Their interests: {{interests}}
The gift: {{gift_idea}}
Why it fits: {{gift_rationale}}
Product: {{product_name}} ({{product_url}}), approx {{price}}
Write the message so it:
Opens warmly and personally (use their first name; no generic salutation).
Names the specific interest and connects it naturally to the gift, so it's clearly chosen for them.
Mentions the gift, but does not include the product link in the message.
Is concise (3-5 sentences), friendly, and sounds like a real human — not salesy.
Ends with a friendly sign-off.
Then produce your final answer as the structured output, filling EVERY field: full_name, title (= their job title), company, interests, gift_idea, product_name, product_url, price all carried through from the context above exactly.personalized_message = the message you wrote.Do not leave any field blank.
```
