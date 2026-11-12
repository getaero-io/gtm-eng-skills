# Google Calendar

An organization owner or admin connects a Google account and configures exact allowed calendar IDs. The connection and allowlist belong to the organization, not the caller. All organization members can use approved calendars. An empty list permits no reads. The `primary` alias is not accepted because it can change on reconnect.

Use list events with an explicit calendar ID, then follow `nextPageToken` until absent. Retain `nextSyncToken` for subsequent incremental reads. Google returns 410 when a sync token expires; rebuild that calendar's snapshot rather than skipping missed changes. Do not combine sync tokens with incompatible query filters. Attendee lists can be incomplete when `maxAttendees` is specified; omit it when matching booking attendees.

The connector does not create meetings, send invitations, change calendar sharing, or grant domain-wide access. The connected Google account must already have access to each approved calendar. Access settings can take up to 45 seconds to propagate through the API-key credential cache. An already admitted request can complete.
