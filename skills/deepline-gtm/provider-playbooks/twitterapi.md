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

## Replies and thread context

`twitterapi_tweet_replies` and `twitterapi_tweet_thread_context` accept the
provider's documented `replies` array and its observed `tweets` array, including
nested `data` envelopes. Both expose the selected results at
`toolResponse.rawV2.data.replies`; original provider fields and pagination are
retained. An explicit empty array returns `no_result`; a missing or malformed
array returns an upstream error. Both arrays can include the original tweet;
thread context can also include surrounding posts. For direct replies to the
requested tweet, filter on `inReplyToId === tweetId`. The full returned array
is preserved and counted for per-item billing, including the original post;
filtering your output does not change the call's billed item count.

## Pagination

Paginated endpoints take a `cursor` (omit or "" for the first page) and return
`has_next_page` + `next_cursor`. Loop on those to page; do not refetch page one.

## Replies and thread context

The unversioned replies and thread-context actions expose records as `replies`.
The provider also returns these records under `tweets`; the adapter preserves
that raw field for existing consumers. The two aliases serialize the same
records twice; process one array rather than combining them. A page can include
the original post, deeper replies, or other context. Check `inReplyToId` when you need direct replies. Returned pages are
not a completeness guarantee, and page sizes vary. Continue with `next_cursor`
while `has_next_page` is true, including after an empty page.

All three actions charge their request minimum on a successful
empty page and report `no_result`. A nonempty context-only page reports
`completed`; it does not establish that direct replies exist.

## Cost

Every request carries a minimum charge, applied even when it returns zero
results. Follower/following/ID pulls are billed per returned item and can get
large fast — prefer `twitterapi_user_followers_ids` for big audiences, and
bound pages/time windows before fanning out. `article`,
`check_follow_relationship`, and `community/info` are fixed higher-cost calls.

Deepline credit pricing for these actions is generated from the provider pricing
metadata and rendered on the public provider pages.
