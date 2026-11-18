# Google Calendar Availability

Personal calls use the connected Google account. A team call selects a named
Google Workspace approval with `connection: 'example.com'` and supplies work
emails from that domain. Use `get_workspace_free_busy` for per-person results,
`get_free_busy` for combined intervals, or `query_free_busy` for Google's
calendar-keyed response. Pass 1–50 emails and a time window up to 14 days.

A known result with no busy intervals is free. Unknown means access or the
provider check failed; never treat it as free. Teams and email lists are Play
inputs, supplied directly or retrieved from a CRM.

For booking, the admin must also approve Calendar events owned access and
verify it in the connection's Enable booking flow. Use
`book_workspace_meeting` with the same domain connection, `organizerEmail`,
a stable Google event `id`, `attendeeEmails`, title, description, and time
window. The meeting belongs to the organizer's primary calendar; invitations
are sent to attendees. The handler checks the organizer's availability again
and persists the booking identity before dispatch.

Reuse the same event ID and inputs after an uncertain result. The handler
recovers an existing matching event instead of sending another invitation.
`get_workspace_meeting` retrieves a Deepline-created meeting by organizer
email and event ID. Concurrent external calendar edits can still race Google's
separate availability and event-insert APIs.

The older booking tools remain an internal OAuth test flow. Workspace booking
uses the explicit Workspace tools above. This provider remains internally gated.
