# From enrollment to outreach

The implemented Play adds eligible contacts to a paused campaign. It does not configure a sequence, activate a campaign or prove delivery. The source-only Play's `outreachStatus` describes that source-only behavior; enrollment has separate outputs.

Before connecting sending, supply a real project brief, expected work, compensation, sender, reply owner and application/briefing destination. Synthetic tasks are not offers to real people.

1. Configure the campaign and sender with the actual opportunity. Keep it paused during enrollment tests.
2. Check role evidence, verified contact data, existing contacts and suppression. A research_pending record is not ready for outreach.
3. Record enrollment, delivery, reply, interest and opt-out separately. Do not infer them from membership.
4. Claim attempts before dispatch. Reconcile uncertain writes against the provider instead of blindly retrying.
5. Update queue states from real events. Honor opt-outs and stop when suppression cannot be checked completely.
6. After accepted work, use availability, payment status and suitable demand to decide whether to make a repeat offer.

The database's `outreach_enabled` flag alone does not implement sending. No script here activates a campaign or installs a recurring trigger.
