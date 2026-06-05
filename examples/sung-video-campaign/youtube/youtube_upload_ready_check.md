# YouTube Upload Ready Check

Checked on 2026-06-05.

## Result

All four Sung campaign videos are ready as private YouTube drafts with final `deepline.com` descriptions and uploaded thumbnail assets recorded in `youtube_upload_results.json`.

The local OAuth token only has `https://www.googleapis.com/auth/youtube.upload`, so YouTube metadata reads and caption uploads fail with insufficient scope. Do not re-upload videos just to check status; use the existing draft URLs below.

## Drafts

| Video | YouTube draft | Privacy | Local video | Thumbnail | Captions |
| --- | --- | --- | --- | --- | --- |
| Waterfall Complexity | https://www.youtube.com/watch?v=OBgolIUXLhQ | private | exists, 3840x2160, 231.0s | exists | exists, not uploaded |
| Provider Sprawl | https://www.youtube.com/watch?v=3gtXZ6UwimE | private | exists, 3840x2160, 374.1s | exists | exists, not uploaded |
| Speedrun Time to Integration | https://www.youtube.com/watch?v=rckDRNylVg8 | private | exists, 3840x2160, 332.8s | exists | exists, not uploaded |
| Pipeline as Code | https://www.youtube.com/watch?v=qecZWS4DerQ | private | exists, 1920x1080, 350.6s | exists | no caption file |

## Checks Run

- `youtube_upload_manifest.json` has four entries.
- `youtube_upload_results.json` has four private draft URLs.
- Every manifest video path exists locally.
- Every manifest thumbnail path exists locally.
- The three caption paths in the manifest exist locally.
- `ffprobe` can read every video file and returns valid duration and dimensions.
- The old `.ai` domain does not appear in any YouTube manifest description.
- All final web references use `https://deepline.com`.

## Known Blockers

- Typefully live draft updates are blocked in `/Users/jaitoor/dev/transcripts` because the local `TYPEFULLY_API_KEY` returns HTTP 403.
- Caption upload requires broader YouTube OAuth scope than the current token has.
