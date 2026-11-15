# Google Calendar Availability

Choose a start and end time at most 14 days apart. Omit calendar IDs for the
connected account’s primary calendar. For team availability, pass individual
secondary calendar IDs that the account can access through Google sharing.

A `known` response contains the combined busy intervals. An `unknown` response
means one or more calendars could not be checked. Do not offer a meeting time
based on an `unknown` response.
