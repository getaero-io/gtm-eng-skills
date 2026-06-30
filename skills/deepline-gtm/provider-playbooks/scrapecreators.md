# ScrapeCreators Guidance

Use ScrapeCreators when the research plan needs public social evidence that generic web search cannot capture well: Reddit comments, TikTok videos/comments, Instagram Reels, and YouTube transcripts/search.

For local-business or restaurant contact recovery, ScrapeCreators is an optional candidate route when the row already has a Facebook or Instagram URL/handle, when Maps/website data is thin, or when a pilot suggests public profile contact fields are where the email lives. Do not make it a required step for every SMB workflow; test it on a tiny sample and keep Maps + website extraction as the default first pass.

Good candidate tools:

- `scrapecreators_facebook_profile`: public Facebook page/profile About data, including business email/phone/address/website when available.
- `scrapecreators_facebook_profile_posts`: recent post text, useful when the About block lacks an email but posts mention catering, reservations, bookings, or contact details.
- `scrapecreators_instagram_profile`: public Instagram profile bio/contact fields, including business public email/contact button/website when available.
- `scrapecreators_instagram_user_posts`: post/caption text, useful when the bio links to booking, menu, or contact pages.

Tool discovery nuance: profile/contact endpoints are research candidates, but if an installed SDK still categorizes them outside `research`, run an unfiltered ScrapeCreators search as a fallback:

```bash
deepline tools search "facebook profile email scrapecreators" --json
deepline tools search "instagram profile bio email scrapecreators" --json
deepline tools search scrapecreators --json
```

When using social profile data for SMB contact email recovery, require identity evidence before accepting the result: match at least two of business name, address, phone, website/menu/booking link, or Google Maps profile. Return the source platform, profile URL, extracted email/contact field, timestamp, and identity evidence columns so the result can be audited.

Pricing note: ScrapeCreators documents these endpoints as 1 credit per request. Deepline billing converts provider credits using the public Business pack rate: $497 / 500,000 credits = $0.000994 per provider credit.
