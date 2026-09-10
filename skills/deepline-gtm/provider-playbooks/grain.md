# Grain

Connect a personal or workspace access token from
[Grain API settings](https://grain.com/app/settings/integrations?tab=api).
Personal tokens see the user's data; workspace tokens can see all workspace data.
Deepline does not bill for these tools. Grain account limits still apply.

List recordings first, then use recording_id for details or JSON transcripts.
Pass the returned cursor to fetch another page. Use include to request optional
participants, highlights, AI summaries, action items, or notes.

Updates, tags, sharing changes, and hook creation/deletion modify Grain data.
Creating a hook also sends a reachability test to hook_url; it must return 2xx.
Creating an upload URL requires filename and, for workspace tokens, user_id.
Upload the file separately to the returned URL. An upload_status hook receives
processing results; the create-upload action itself does not upload a recording.

Team sharing, OAuth exchange, binary downloads and text exports are not exposed.
See docs.txt for the conflicting team-sharing URL and exact excluded operations.
