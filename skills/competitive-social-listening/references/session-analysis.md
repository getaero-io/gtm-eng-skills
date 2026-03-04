# Session Analysis: Competitive Social Listening (March 2026)

Source session: `ad45418c-668a-4865-a449-2f34af4c3ce4`
Companies: Vooma, GoAugment, TryPallet
Final output: 4,131 senior engagements from 208 posts

---

## Issues, Time Impact, and Skill Fixes

### Issue 1 — Apollo `organizations` vs `accounts` field
**What happened:** JS extractor used `d.accounts` but Apollo returns `d.organizations`. All 3 company domain lookups returned null. Had to debug, rewrite extractor, re-run enrichment.
**Time lost:** ~20 minutes (3 failed runs + debugging)
**Skill fix:** `extract_company.js` template uses `d.organizations || d.accounts` with comment. Pitfalls table calls this out explicitly.

---

### Issue 2 — JS file path (relative vs absolute)
**What happened:** `run_javascript:@/extract_company.js` failed with `No such file or directory` because `$WORKDIR` wasn't resolved. Had to debug path handling.
**Time lost:** ~10 minutes (2 failed enrich runs)
**Skill fix:** Skill enforces absolute paths in all examples. Note in pitfalls table.

---

### Issue 3 — `harvestapi/linkedin-company-employees` returns empty
**What happened:** Agent tried Apify's company employees actor first (it's in actor-contracts.md). Got 0 results for all 3 companies. Switched to `dropleads_search_people`.
**Time lost:** ~25 minutes (discovery + 3 failed actor runs)
**Skill fix:** Skill routes to dropleads immediately for employee discovery. Apify employees actor is not mentioned. Pitfall explicitly calls out this dead end.

---

### Issue 4 — Dropleads wrong filter format
**What happened:** Used `"companyDomains": {"include": ["vooma.com"]}` (object format). Got 0 results. Fixed to plain array `"companyDomains": ["vooma.com"]`.
**Time lost:** ~15 minutes (2 failed runs + format debugging)
**Skill fix:** Payload examples use correct plain array format. Pitfall table calls out the wrong format explicitly.

---

### Issue 5 — Tried crustdata_linkedin_posts before Apify post URL approach
**What happened:** Agent tried `crustdata_linkedin_posts` for post scraping, which doesn't support reaction/comment fetching in the same call. Then tried `apify_run_actor_sync` with multiple profile URLs + reactions enabled — consistently timed out (CLI timeout ~90s, actor takes >120s).
**Time lost:** ~45 minutes (3 different approaches before discovering the post URL batching method)
**Skill fix:** Skill goes directly to `harvestapi/linkedin-company-posts` for posts (no reactions), then batches post URLs for reaction scraping. Crustdata is not used for this workflow. The key insight (post URLs as targetUrls) is documented prominently.

---

### Issue 6 — `apify_run_actor_sync` timeouts for reaction scraping
**What happened:** Reaction scraping across 25 URLs takes 3-5 minutes. CLI timeout is ~90s. Every sync call failed with exit code 4. Took many attempts to discover the async split approach.
**Time lost:** ~60 minutes (multiple timeout cycles, retrying, debugging)
**Skill fix:** Skill uses async `apify_run_actor` (captures datasetId), then downloads separately. `apify_run_actor_sync` is explicitly NOT recommended for reaction scraping.

---

### Issue 7 — CSV field size limit (131072 bytes) with deepline enrich
**What happened:** Attempted to store large Apify JSON responses in CSV cells via `deepline enrich`. Got `_csv.Error: field larger than field limit`. Deepline's CSV engine has a 131KB cell limit.
**Time lost:** ~20 minutes (failed enrich attempts, debugging CSV limit)
**Skill fix:** Skill never routes Apify response data through deepline enrich CSV cells. Downloads dataset items directly with `apify_get_dataset_items` to standalone JSON files.

---

### Issue 8 — 21 parallel batches caused 2 timeouts (batches 00 and 03)
**What happened:** Fired all 21 batches simultaneously. Batches 00 and 03 timed out (likely server-side concurrency throttle). Had to re-run.
**Time lost:** ~15 minutes (2 retries)
**Skill fix:** Skill specifies max 15 parallel batches. Group large batch sets into sequential groups.

---

### Issue 9 — Viral posts (>300 reactions) consistently timeout
**What happened:** Batch 00 contained the top-10 highest-engagement posts (707, 366 reactions). Every run timed out regardless of batch size. Needed reduced `maxReactions: 50` to complete.
**Time lost:** ~30 minutes (4 failed attempts before discovering the limit reduction fix)
**Skill fix:** `build_batches.py` separates posts with >300 total reactions into dedicated batches with `maxReactions: 50`. Normal posts use 100.

---

### Issue 10 — deepline CLI output has "Status/Job ID/Result" header
**What happened:** `apify_get_dataset_items` output prefixed with multi-line header. `json.load()` failed. Had to implement `re.search(r'(\{|\[)', content)` parser.
**Time lost:** ~10 minutes
**Skill fix:** `parse_engagements.py` script uses the header-skip parser. Documented in pitfalls.

---

### Issue 11 — `source_url` empty in posts CSV
**What happened:** The posts dataset from Apify has `source_url` consistently empty. Couldn't map posts back to companies. Had to extract LinkedIn handle from post URL and match against `all_urls.csv`.
**Time lost:** ~15 minutes
**Skill fix:** `all_urls.csv` is explicitly designated as company mapping source of truth. `extract_handle()` function handles post URL → handle extraction.

---

### Issue 12 — Wrong `deepline csv render` command
**What happened:** Used `deepline csv --render-as-playground start` (not a real command). Got `Unknown csv command` error.
**Time lost:** ~5 minutes
**Skill fix:** Correct command documented: `deepline csv render start --csv FILE --open`

---

## Summary

| Category | Issues | Total Time Lost |
|---|---|---|
| Wrong provider/actor | Issues 3, 5 | ~70 min |
| CLI timeouts | Issues 6, 8, 9 | ~105 min |
| Data format / parsing | Issues 1, 4, 10, 11 | ~60 min |
| Path / command errors | Issues 2, 12 | ~15 min |
| Architecture (CSV limits) | Issue 7 | ~20 min |
| **Total** | **12 issues** | **~270 min (4.5 hrs)** |

With this skill, the same workflow should complete in **45-60 minutes** end to end.
