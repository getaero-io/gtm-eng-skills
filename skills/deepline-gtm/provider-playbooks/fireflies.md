# Fireflies.ai

Start with `fireflies_transcripts` to discover meeting IDs. Use `limit` and `skip` to paginate; Fireflies allows at most 50 transcripts per request. Use `keyword`, date bounds, organizers, participants, channel, host, or `mine` to narrow the list.

Use `fireflies_transcript` when you need the full meeting record. It includes sentences, summaries, analytics, attendee data, `transcript_url`, `audio_url`, and `video_url`. Fireflies exposes recordings through transcript media URLs rather than a separate videos endpoint.

Use IDs returned by list actions for channel, bite, AskFred, live-meeting, sharing, and update actions. Treat delete, upload, share, role, AskFred, and meeting-update actions as writes: confirm user intent and exact IDs before execution.

`fireflies_rule_executions_by_meeting` and `fireflies_audit_events` may require an enterprise Fireflies plan. All actions require a customer-owned Fireflies API key. Deepline does not bill for Fireflies usage.
