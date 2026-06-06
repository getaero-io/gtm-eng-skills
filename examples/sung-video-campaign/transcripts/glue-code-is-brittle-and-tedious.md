# Glue Code Is Brittle And Tedious Transcript

Source video: `https://drive.google.com/file/d/17kNL62Rf_EC--jTO2Ds4BwZRQxKM0IfY/view`

Drive title: `Glue Code is Brittle and Tedious.mp4`

Status: `blocked-download`

## Download Attempts

2026-06-06:

- Google Drive connector metadata succeeded.
- Google Drive connector raw fetch failed with `Could not get file`.
- Local Drive OAuth token returned `File not found` for file ID `17kNL62Rf_EC--jTO2Ds4BwZRQxKM0IfY`.
- Direct Drive download returned an HTML page, not MP4 bytes.
- `yt-dlp --cookies-from-browser chrome` returned HTTP 403 across local Chrome profiles.

## Next Step

Save the raw export locally as:

```text
examples/sung-video-campaign/videos/glue-code-is-brittle-and-tedious.mp4
```

Then run:

```bash
whisper examples/sung-video-campaign/videos/glue-code-is-brittle-and-tedious.mp4 \
  --model small \
  --output_dir examples/sung-video-campaign/youtube/captions \
  --output_format all
```

Move the generated `.txt` transcript into this file and use the `.srt` file as:

```text
examples/sung-video-campaign/youtube/captions/glue-code-is-brittle-and-tedious.srt
```
