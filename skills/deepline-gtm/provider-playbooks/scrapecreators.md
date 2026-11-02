# ScrapeCreators Guidance

Use ScrapeCreators when the research plan needs public social evidence that generic web search cannot capture well: a brand's or creator's own posts on TikTok, Instagram, YouTube, X, LinkedIn, Facebook, Threads, Bluesky, Pinterest, Twitch or Reddit; comments and transcripts; keyword and hashtag searches; and the Meta, Google, TikTok and LinkedIn ad libraries.

Pick the tool by the identifier you hold:

- A handle or profile URL → the platform's `*_profile` tool for bio, links and counts; its `*_user_posts` / `*_profile_videos` / `*_channel_videos` / `*_user_tweets` / `*_company_posts` tool for the content feed (page with the cursor or continuation token the response returns).
- A post, video, tweet or reel URL → the platform's single-item tool, then `*_comments` for the discussion and `*_transcript` for spoken content.
- A keyword → `*_search` tools; use `scrapecreators_tiktok_search_suggestions` or `scrapecreators_youtube_search_typeahead` to expand queries first.
- A company name or domain → `scrapecreators_facebook_adlibrary_company_ads`, `scrapecreators_google_company_ads`, `scrapecreators_linkedin_ads_search`, `scrapecreators_tiktok_ad_library_search` for live creatives.
- A creator handle → `scrapecreators_find_creator_emails` and `scrapecreators_find_social_profiles` for contact and cross-platform discovery.

For local-business or restaurant contact recovery, ScrapeCreators is an optional candidate route when the row already has a Facebook or Instagram URL/handle, when Maps/website data is thin, or when a pilot suggests public profile contact fields are where the email lives. Do not make it a required step for every SMB workflow; keep Maps + website extraction as the default first pass. For larger or uncertain authorized recovery work, test the route on a tiny sample before scaling. A small supplied Play needs no extra pilot or repeated approval, and inspecting its results does not authorize paid recovery or repair.

Good candidate tools for SMB contact recovery:

- `scrapecreators_facebook_profile`: public Facebook page/profile About data, including business email/phone/address/website when available.
- `scrapecreators_facebook_profile_posts`: recent post text, useful when the About block lacks an email but posts mention catering, reservations, bookings, or contact details.
- `scrapecreators_instagram_profile`: public Instagram profile bio/contact fields, including business public email/contact button/website when available.
- `scrapecreators_instagram_user_posts`: post/caption text, useful when the bio links to booking, menu, or contact pages.

When using social profile data for SMB contact email recovery, require identity evidence before accepting the result: match at least two of business name, address, phone, website/menu/booking link, or Google Maps profile. Return the source platform, profile URL, extracted email/contact field, timestamp, and identity evidence columns so the result can be audited.

Options that change the Deepline price: `download_media`, `get_ad_details`, `include_replies` and `allow_long_transcription` make a call several times more expensive; leave them off unless the row needs the media file, full ad creative, reply tree or a transcript longer than two minutes. `cache_max_age` returns a recent cached response at no charge when one exists.

Pricing note: Deepline credit pricing for these endpoints is generated from the provider pricing metadata and rendered on the public provider pages.
