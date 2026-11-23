# Measure useful work and return visits

**Activated:** an expert's first human-accepted production contribution. Signups, practice tasks and campaign membership do not count.

**Retained contributors, trailing 28 days:** experts with an accepted artifact in the last 28 days and a different accepted artifact before that window.

Report that count alongside newly activated experts and **cohort retention**: the share with another accepted artifact in days 30–60 after activation, among experts observed for the full 60 days.

## Find the step that needs attention

| Step | Measure |
|---|---|
| Discover | Unique identity-resolved candidates / returned profiles |
| Qualify | Domain-approved experts / completed domain reviews |
| Recruit | Positive replies / delivered invitations |
| Onboard | Ready within 7 days / interested experts observed for 7 days |
| Match | Accepted assignment within 7 days / ready experts observed for 7 days |
| Review | First accepted work within 30 days / ready experts observed for 30 days |
| Retain | Repeat accepted work in days 30–60 / activated experts observed for 60 days |

Track waiting by reason, owner and age. Record why people decline. Compare retention with suitable offers made and payment delays: someone cannot accept work you never offered.

## Calculate consistently

Use stable expert, artifact and event IDs with UTC timestamps. Count revisions of one artifact once. Exclude synthetic and practice records; remove withdrawn acceptances. Use half-open time windows and report zero denominators as unknown. Do not count immature cohorts as failures.

[The calculator](metrics/calculate.py) demonstrates activation and retention on [synthetic events](metrics/events.csv). Other step measures need the corresponding production events; no live dashboard is included.

```sh
python3 metrics/calculate.py metrics/events.csv --as-of 2026-11-22T00:00:00Z --synthetic
```

The observation windows are starting definitions. Adjust them to actual task cadence, while keeping quality, payment and opt-outs visible.
