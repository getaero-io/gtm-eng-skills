# TwitterAPI.io Guidance

Managed X/Twitter data API. Auth is a provider-level `X-API-Key`; all operations
are GET reads. Use these instead of scraping x.com.

## Picking an operation

- Tweet search: `twitterapi_advanced_search` (include `since:YYYY-MM-DD` in the
  query for last-30-days research). Community-wide search: `twitterapi_community_search`.
- A profile: `twitterapi_user_info` (by userName) or `twitterapi_batch_user_info`
  (many userIds at once) or `twitterapi_user_about` (extended profile).
- A user's tweets: `twitterapi_user_last_tweets` or `twitterapi_user_timeline`.
- Audience: `twitterapi_user_followers` / `twitterapi_user_followings` (full
  profiles, pageSize 20-200) or `twitterapi_user_followers_ids` (IDs only, up to
  5,000/page — far cheaper for large audiences) or `twitterapi_verified_followers`.
- Relationship: `twitterapi_check_follow_relationship`. User discovery: `twitterapi_user_search`.
- Around a tweet: `twitterapi_tweet_replies` (or `_v2` for ranked), `_quotations`,
  `_retweeters`, `_thread_context`. Hydrate known IDs: `twitterapi_tweets_by_ids`.
  Long-form: `twitterapi_article`.
- Lists: `twitterapi_list_timeline`, `twitterapi_list_followers`, `twitterapi_list_members`.
- Communities: `twitterapi_community_info` / `_members` / `_moderators` / `_tweets`.
- Trends: `twitterapi_trends` (needs a WOEID). Spaces: `twitterapi_space_detail`.
- Account/credits: `twitterapi_my_info`.

## Pagination

Paginated endpoints take a `cursor` (omit or "" for the first page) and return
`has_next_page` + `next_cursor`. Loop on those to page; do not refetch page one.

## Cost

100,000 credits = $1.00, with a $0.00015 minimum per request (charged even on
zero results). Follower/following/ID pulls are billed per returned item and can
get large fast — prefer `twitterapi_user_followers_ids` for big audiences, and
bound pages/time windows before fanning out. `article`, `check_follow_relationship`,
and `community/info` are fixed higher-cost calls (100/100/20 credits).
