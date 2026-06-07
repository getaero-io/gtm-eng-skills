# Sung GTM Engineering Video Campaign

This folder packages the Sung walkthroughs for review, YouTube upload, and blog/social reuse.

## Source Context

- Slack channel: `#deepline-sung`
- Google Drive folder: `https://drive.google.com/drive/folders/1GZJ5UOllyzTvLaR6T2lts9LIWM3Gpf2k`
- Screen Studio polished links:
  - Waterfall Complexity: `https://screen.studio/share/joR0OS9O`
  - Provider Sprawl: `https://screen.studio/share/ZdbnwTVR`
  - Speedrun Time to Integration: `https://screen.studio/share/9jg1eUgz`
  - Pipeline as Code: `https://screen.studio/share/3snYuVcd`
  - Glue Code is Brittle and Tedious: `https://drive.google.com/file/d/17kNL62Rf_EC--jTO2Ds4BwZRQxKM0IfY/view`

## Publishable Videos

| Video | Local file | Thumbnail | Blog draft |
| --- | --- | --- | --- |
| Waterfall Complexity | `videos/waterfall-complexity-polished.mp4` | `thumbnails/waterfall-complexity.png` | `blog-posts/waterfall-enrichment-workflow-engineering.md` |
| Provider Sprawl | `videos/provider-sprawl-polished.mp4` | `thumbnails/provider-sprawl.png` | `blog-posts/provider-sprawl-gtm-workflows.md` |
| Speedrun Time to Integration | `videos/speedrun-time-to-integration-polished.mp4` | `thumbnails/speedrun-time-to-integration.png` | `blog-posts/snowflake-crm-campaign-workflow.md` |
| Pipeline as Code | `videos/pipeline-as-code-screenstudio.mp4` | `thumbnails/pipeline-as-code.png` | `blog-posts/pipeline-as-code-account-mapping.md` |
| Glue Code is Brittle and Tedious | `videos/glue-code-is-brittle-and-tedious.mp4` | TBD | `blog-posts/glue-code-gtm-workflows.md` |

## Social Drafts

Updated Typefully/source social copy lives in `social-hooks/`.

- `social-hooks/typefully-researched-drafts.md`: final source of truth with YouTube draft URLs and Deepline blog URLs.
- `social-hooks/typefully-draft-links.md`: existing Typefully draft IDs plus live API blocker note.
- `social-hooks/typefully-linkedin-video-drafts.md`: LinkedIn-only Typefully drafts with native video attached.
- `social-hooks/all-platform-hooks.md`: X, LinkedIn, and Threads hook bank.
- `social-hooks/snowflake-lead-magnet-drafts.md`: X and LinkedIn launch drafts for the Snowflake PQL setup guide.

## Lead Magnets

- `lead-magnets/snowflake-pql-campaign-playbook.md`: setup guide with Snowflake product usage query, dbt model, PLG/GTM workflow examples, and Deepline/Aero workflow play for the Speedrun Time to Integration post. Notion share page: `https://app.notion.com/p/Snowflake-PQL-to-Campaign-Playbook-377da8d1d8eb8128b1bde0d84216bf2a`.

## YouTube Draft Upload Status

The upload script publishes private drafts by default.

Current readiness check: `youtube/youtube_upload_ready_check.md`.

| Video | Status | URL |
| --- | --- | --- |
| Waterfall Complexity | Uploaded private draft; on-brand thumbnail set; description uses `deepline.com`; captions skipped due OAuth scope. | `https://www.youtube.com/watch?v=OBgolIUXLhQ` |
| Provider Sprawl | Uploaded private draft; on-brand thumbnail set; description uses `deepline.com`; captions skipped due OAuth scope. | `https://www.youtube.com/watch?v=3gtXZ6UwimE` |
| Speedrun Time to Integration | Uploaded private draft; on-brand thumbnail set; description uses `deepline.com`; captions skipped due OAuth scope. | `https://www.youtube.com/watch?v=rckDRNylVg8` |
| Pipeline as Code | Uploaded private draft; on-brand thumbnail set; description uses `deepline.com`. | `https://www.youtube.com/watch?v=qecZWS4DerQ` |

## Rough Cuts Archived

- `videos/waterfall-complexity-rough.mp4`
- `videos/provider-sprawl-rough.mp4`
- `videos/speedrun-time-to-integration-rough.mp4`

## Missing Source File

Sung attached `account-mapping.play.ts` in Slack as file ID `F0B7GKWU0F7`. The Slack connector can see the file metadata, but file download currently fails because the workspace token is missing the required file-read scope. If the scope is granted later, download it into `source-files/account-mapping.play.ts`.

## Caption Status

SRT captions for the three polished Drive videos are included in `youtube/captions/`. Uploading captions requires a broader YouTube OAuth scope than the current local token has. The videos were still uploaded as private drafts with titles, descriptions, tags, and thumbnails.

The Glue Code raw export is tracked, but transcription is blocked until the Drive file can be downloaded locally. The placeholder transcript and failed download attempts are recorded in `transcripts/glue-code-is-brittle-and-tedious.md`.

## Commands

Generate thumbnails:

```bash
python3 examples/sung-video-campaign/scripts/build_thumbnails.py
```

Upload private YouTube drafts:

```bash
python3 examples/sung-video-campaign/youtube/upload_youtube.py \
  --manifest examples/sung-video-campaign/youtube/youtube_upload_manifest.json \
  --results examples/sung-video-campaign/youtube/youtube_upload_results.json
```

The upload script defaults to the existing local YouTube OAuth files under `/Users/jaitoor/Downloads/april-tools-day-segments/youtube/`. Override with `YOUTUBE_TOKEN_PATH` and `YOUTUBE_CLIENT_SECRET_PATH` if needed.
