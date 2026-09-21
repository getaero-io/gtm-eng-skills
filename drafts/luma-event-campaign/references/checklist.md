# Event Campaign Checklist

## Pre-launch (T-14 days)

- [ ] Luma event page live with venue, date, speakers
- [ ] Capacity limit set
- [ ] ICP / TAL sheet finalized
- [ ] Guest list sourced (export or API pull)
- [ ] Enrich pilot complete (≤10 rows)
- [ ] Messaging templates reviewed and approved
- [ ] Sequencer campaign created in **paused** state

## Launch (T-7 days)

- [ ] Full enrich run complete
- [ ] Scoring applied: hot / warm / low / skip
- [ ] Campaigns loaded: email + LinkedIn sequences
- [ ] Social posts drafted and scheduled
- [ ] Human review of first 20 messages
- [ ] Campaigns **still paused** until final approval

## Approval gate

- [ ] Review send list: no unsafe emails, no obvious mismatches
- [ ] Confirm personalization tokens populated correctly
- [ ] Check unsubscribe / opt-out links present
- [ ] Final signoff from event owner

## Live (post-approval)

- [ ] Campaigns unpaused
- [ ] Monitor: open rates, reply sentiment, bounce/unsubscribe
- [ ] Registration webhook live (see `luma-inbound-webhook-enrich`)

## Day-of (T-0)

- [ ] Hand off to `event-ops-score-and-door` for capacity management
- [ ] Hand off to `event-host-prep-dossiers` for host prep (optional)
- [ ] Door list printed or loaded on tablet

## Post-event (T+2 days)

- [ ] Show/no-show writeback to CRM
- [ ] Post-event follow-up sequences staged (paused)
- [ ] Retrospective: hit rate, show rate, pipeline created
