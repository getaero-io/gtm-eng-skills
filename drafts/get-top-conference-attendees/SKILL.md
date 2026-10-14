---
name: get-top-conference-attendees
description: >-
  Takes in (or finds) attendees you should connect with at your next conference, ranks and
  researches them, and adds them — along with their full research dossiers — to your Deepline
  customer DB (storage.conference_attendees, linked to storage.conference_companies) so you can
  enrich further with Deepline plays or take action on them.
category: build-lists
personas: [account-executive, founder]
mechanism: script
touches: writes-records
keywords: [event-follow-up, lead-scoring]
ported_from: clay-run/clay-skill-creator/skills/shy-rahnama/get-top-conference-attendees
---

# Get top conference attendees (re-read the campaign; never remember what changed)

**The insight, and it decides the whole shape: nothing can tell this skill what got
unlocked.** A free account gets a small number of fully written dossiers per campaign;
everything else is ranked and waiting. Unlocking more happens in a browser, against a share
link, by a person who may not be the person who ran this — possibly on their phone, possibly
next week.

The skill CAN unlock dossiers itself — there is an endpoint for it, priced and gated at
Step 9. But that is not the same as being told about one. There is **no `since` or
`updated_after` parameter on any call**, **no webhook for an unlock**, and nothing in any
contact record saying when its dossier appeared. Unlocking also still happens in the browser,
by whoever has the share link.

So the skill can never be sure it was the one that unlocked anything. A top-up cannot be a
notification, and it cannot be a diff against a remembered timestamp. It can only be a
re-read. **The campaign id is the entire state.** Every load asks for every contact again,
takes everything that now carries a dossier, subtracts what has already been written, and
writes the difference.

That is what makes both paths the same path. Whether this skill spent the credits a minute
ago or somebody clicked through a share link last Tuesday, the command is identical and the
result is correct — and on a campaign where nothing changed it writes nothing and says so.

**The second decision follows from the first: the ledger must not be load-bearing.** If
"what have I already written" lived only in a local file, then a lost file would mean either
duplicates or a manual reconciliation. So every write is an upsert keyed on the attendee's
own LinkedIn URL or email — the same person written twice is updated, not duplicated. The
ledger makes a re-run cheap; it is not what makes it correct. That is what makes the whole
thing safe to interrupt at any point.

**And the third: the dossier is the product, and it is the thing a typed table cannot hold as
it arrives.** A dossier is nested — lists of buying signals, lists of openers, a tier, a score.
Table columns are flat scalars. Flatten it carelessly and you get a column holding a Python
repr that matches no filter anybody would write. Worse, a value the column's type cannot parse
fails the whole multi-row statement, so one score of `80-90` unsettles a hundred attendees.
(Measured in Clay Audiences, where this skill was first built, the same value was *accepted*
and then invisible to every filter — a different failure with the same cure.) So each piece of
a dossier is placed deliberately: `tier` and `score` become things you can segment on, the
prose becomes prose, and a score that arrives as a range is **dropped and named as dropped**
rather than sent.

> Do not start a step before the steps above it have their answers. If a declared input is
> missing, ask for it — never assume a default and continue.

> **Report Lanyard's results straight, and neither oversell nor prosecute them.** This is
> easy to get wrong in the honest direction. A real run opened its summary with *"none of
> these five has evidence of attending the 2026 edition"* and closed with *"given the
> attendance and fit gaps, review the results before adding credits"* — every word true, and
> the overall effect was a brief against the service the person had just chosen to use.
>
> The rules that keep it straight:
>
> - **Lead with what they got**, then with what it is useful for, then with anything that
>   qualifies it. Not the reverse.
> - **Report limits as properties of the DATA, not verdicts on the vendor.** "Every record
>   says which edition its evidence comes from, and three of these five point at last year"
>   is the same fact as "none of them is confirmed for 2026", and one of them hands over a
>   filter while the other hands over a grievance.
> - **Never advise for or against spending.** Give the count, the price and the balance, and
>   stop. "Review before you pay" is a judgment about someone else's product that nobody
>   asked for, and it is being made on a single run.
> - **Do not narrate the service's internals as trouble.** A stage that repeats, or a run
>   longer than the estimate, is a big event being processed. Say what is happening; do not
>   diagnose a retry loop you cannot see.
> - **And do not tip into salesmanship either.** Somebody at Lanyard may read this file and
>   so may somebody deciding whether to trust the list. Accurate and plainly put serves both;
>   flattery serves neither, and a caveat deleted to keep the tone warm is the one failure
>   worse than a blunt one.

> **Say what is about to happen before it happens, every time — not only at the gates.** A
> person following this should never be surprised by a step, and should never have to infer
> what a question is for. One plain sentence before each move: what you are about to do, and
> why this question is being asked now. That costs a line and buys the difference between
> being walked through something and being interrogated by it. The places it matters most are
> the ones where nothing visible happens for a while, or where something lands in their
> workspace or their wallet.

> **Every question goes through the harness's dialogue card — every one, without
> exception.** Not a question typed into the conversation, not a numbered list, not "let me
> know either way". The card is what makes an answer one click instead of a sentence, and a
> skill that uses it for some questions and prose for others feels broken in a way nobody can
> name. Where the answer space is closed, the options ARE the answer. Where it is genuinely
> open — the conference name, the sentence describing who is worth meeting — still ask on a
> card and let them use its free-text box; never invent fake options just to fill one.

> **Ask only what changes the outcome.** The table columns, the match keys, the writer
> lanes and the output contract are all prescribed below and none of them is a question. If
> you find yourself about to ask which fields to create, which contacts to write, or whether
> to use a table — the answer is already in this file.

> **This skill is not finished when the campaign completes.** It is finished when the rows
> are in the customer DB, the counts have been verified with a query, and the person has
> been told plainly how many are still locked and what to do about it. If you stop early, say
> which step, what remains, and the exact command that resumes it.

## Declared inputs

**Nothing here ships with a value.** Where a default is defensible it is named, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Which conference** | the event's name, and a city or year when the name alone is ambiguous | **ask, as free text** — the answer space is every event in the world and no list covers it. No default and no guess: a conference that runs annually in three cities has no single right answer |
| **The right edition, confirmed** | a click: yes / wrong edition / not that event | **ask as a CHOICE, not a paragraph.** The lookup is free, so confirm this before collecting anything else — a wrong edition makes every other answer worthless |
| **Which company is going** | a click, or a typed domain. Everything is scored against it | **ask FIRST, before the conference, offering guesses as options** — the Lanyard email's domain with any plus-addressing stripped, and the Deepline workspace name. Never adopt either silently: an agency, a contractor or a personal address makes the email's domain the wrong company, and a free-mail address means nothing at all. Without the right domain every score is wrong in a way nothing reveals |
| **What a good person to meet looks like** | a multi-select of clients / partners / investors / hires, then one line of specifics | **ask the categories as a CHOICE** — the API's own `goals.categories` is a closed set. Then ask the specifics as free text: that sentence becomes the rubric, and "anyone senior" produces a list ranked on seniority |
| **Who is going from your side** | a click: just me / nobody / let me list them | **ask once, offering those options.** It shapes how dossiers are framed; absent, they are framed generically |
| **Where the working files live** | a durable directory | **decide it, say so, and move on — do not block on it.** The config, the ledger and `writer-config.json` must outlive the session: the whole point is running the same `load` weeks later. A scratch or temp directory is the wrong answer even when the session starts in one |
| **Which email to use for Lanyard** | a click: keep the email already set up, or use a different one | **ask, showing the email — and ask nothing about keys.** A saved account is not consent to spend from it: the campaign runs in it and the credits come out of it. This is NOT the Deepline workspace; the two are unrelated and belong to different people as often as not |
| **An email, when no account exists yet** | an email, then the code sent to it | **ask only when there is none.** An account that already exists is a choice of email, not a sign-up |
| **An attendee list, if they have one** | a click (this year's / last year's / no), then a CSV path | **ask — nobody volunteers it.** No default and no upload: 500 or fewer are sent inline with the campaign. `no` is a complete answer and the service finds attendees itself |
| **Deepline, signed in, with the customer DB reachable** | **nothing — do not ask.** `deepline auth status --json` and a read of `information_schema.columns` either answer or they do not | if either fails, say which command failed and stop. There is nothing to write into. CLI missing: `npm install -g deepline && deepline auth register --wait auto` |

**And these are derived or defaulted, not asked. Each appears in the plan at Step 5 so the
person can SEE it before anything runs — not so it can be renegotiated there. Only the first
two are adjustable at all, and both are config keys rather than questions; the last three
cannot change without a rebuild:**

- **How many dossiers to ask for** — 25 by default, and the service caps it at its own
  maximum while a free account caps it far lower. The plan states what was asked for; the run
  reports what was actually allowed.
- **Whether company rows are written** — yes, for every attendee whose company has a
  domain, with the person linked to it. Attendees whose company has no domain are written
  unlinked, never dropped.
- **Which columns exist, and their types** — prescribed. See `references/audience-model.md`.
- **Which attendees are written** — everyone who has a dossier. Not a selection.
- **Which match key identifies a person** — LinkedIn URL first, email second.

## What this skill touches

- **Reads** — the conference campaign and its contacts from Lanyard; your Deepline
  workspace id and the customer DB's `information_schema.columns` for the two tables.
- **Writes** — customer-DB **rows** via `deepline db query`: one row in
  `storage.conference_attendees` per attendee with a dossier, and one row in
  `storage.conference_companies` per company domain, linked by `company_domain`. Creates the
  two tables (or adopts them, adding missing columns) as listed in
  `references/audience-model.md`. Appends a local ledger file under
  `~/.deepline-conference-writer/`, outside any repository.
- **Never** — deletes a row, clears a populated column, writes an attendee who has no
  dossier, drafts or sends a message, enrols anyone in a sequence, pushes anything to a CRM,
  puts your API key on a command line, or prints it.
- **Halts** — Step 3 `other`, Step 5 `spend-approval`, Step 5 `write-approval`, Step 9
  `spend-approval`.
- **Vendor-specific** — Lanyard (`lanyard.redlinegrowth.com`). It is the whole source of
  attendees, scores and dossiers. Without an account there is no reduced mode: the skill does
  not run. An account is free to create and a free account gets a limited number of dossiers
  per campaign.
- **Derived from** — Lanyard's own build brief for this skill, author-confirmed, plus its live
  API read on 2026-09-16. Three blocks the brief documents are not in the published schema;
  they are read when present and derived when absent, and the run says which. See
  `references/attendee-api.md`.

## What ships in this package

| File | What it is for |
|---|---|
| `scripts/conference-config.example.json` | A complete config with every key explained. Start here. It holds no credentials and must never be given any. |
| `scripts/build_conference_writer.py` | Creates or adopts the two customer-DB tables and their columns. Run once per workspace; re-running adds only the gap. |
| `scripts/drive_load.py` | Everything at run time: which Lanyard account, list campaigns, run one, load and top up, price and buy unlocks. The command the installer lives in. |
| `scripts/attendee_list.py` | Reads a CSV or TSV attendee list the installer already has into campaign seed input. No upload endpoint involved. |
| `scripts/lanyard_lib.py` | The attendee-service client plus every pure reshaping function: dossier states, the flattening, the top-up delta, the unlock suggestion. |
| `scripts/audience_lib.py` | The column plan, the value validation that keeps unparseable values out of a batch, and the routing decision that picks a match key and lane. |
| `scripts/conference_lib.py` | The DB side: paths, SQL literal quoting (the trust boundary), DDL, column adoption, the upsert, and the one `deepline db query` call. Handles no credentials of any kind. |
| `scripts/test_offline.py` | 288 checks over all of the above, with no platform, no network and no credentials. Run it before trusting a change. |
| `references/attendee-api.md` | The API as measured — shapes, limits, and where the service has moved ahead of its published spec. |
| `references/audience-model.md` | Both tables, every column, its type, and why that type. |

## Step 0 — Say what this is, check the platform, and put the files somewhere durable

**Open by saying what this is, because almost nobody installing it has heard of Lanyard.**
They came for conference attendees; they did not come to sign up for a product whose name
means nothing to them. Being asked for an email by an unexplained third party is the point
where a reasonable person stops.

So the first thing said, in your own words, is what the skill does:

> *"This skill uses a service called Lanyard to find the best people to connect with at an
> upcoming conference, based on your goals. It is free to sign up for and gives you a handful
> of full write-ups per conference, and I will put the results into your Deepline customer
> database."*

Then say, in one more sentence, what the next few minutes look like: a couple of questions
about you and the event, then a plan to approve before anything is created or spent.

Say it **before** the first question, not as a footnote to it. If they ask what Lanyard is
after you have already asked for their email, the introduction came too late.

```bash
deepline auth status --json
deepline db query --sql "select table_name, column_name from information_schema.columns where table_schema = 'storage' and table_name like 'conference_%'" --json
```

Name the workspace out loud (`workspace.name`). Then say, in one sentence, what this run will
touch: *"This writes attendee and company rows into two tables in <workspace>'s Deepline
customer DB, creating them if they are not there yet, and reads a conference campaign from
Lanyard. It sends nothing to anyone."*

**Then decide where the working files go, state it in one line, and carry on.** Three files
have to outlive this session — the config, `writer-config.json`, and the ledger — because the
skill's whole promise is that the same `load` command works in three weeks when somebody
unlocks more dossiers. `writer-config.json` in particular is what lets a cold session find
the workspace, the key and the ledgers without anything from this run.

**Every file this run produces goes in `~/.deepline-conference-writer/<workspace id>/runs/<date>/`
— the config, the campaign result, the notes — and say so in one sentence.** `scripts/
conference_lib.py` computes that path (`run_dir`), so read it from there rather than composing
one. Durable by construction, next to the writer state and the ledgers that already live
there, so a session months later finds everything in one place. Create the directory, write
the config into it, and run every command with that config's full path. Do not stop to ask —
name the choice and let it be corrected.

The two files the scripts place themselves — the per-campaign ledger and `campaigns.jsonl` —
go beside the writer automatically and ignore wherever the config sits. That is deliberate:
the breadcrumbs a later session needs must not depend on a folder somebody tidied away.

**Never inside a git repository**, and this is the part that bites. Three separate cold runs
each invented their own folder — `runs/`, `conference-runs/`, `.conference-runs/` — all of
them inside the repo the session happened to start in. The instinct is right (a repo is
durable) and the consequence is not: this output carries real email addresses, the path a key
was written to, and **live share tokens**, and an untracked file in a repo is one `git add -A`
away from being committed and pushed. A dot-prefixed name is worse, not better: it hides the
problem from a casual `ls` without hiding it from `git add`.

**Where the work happens, because that is what it costs.** The attendee research, the scoring
and the dossiers all happen on Lanyard's side and take real time — five to twenty minutes for
a campaign. Reshaping, validating and routing happen locally and are free. The writes are
`deepline db query` statements against your own customer DB; no provider is called and no
Deepline credit is spent by a load. **The cost of this skill is the campaign, not the load.**

## Step 1 — Whose account, and sign in only if there is no key

**Two different accounts are in play, and confusing them is the trap here.** Step 0 checked
the **Deepline workspace** with `deepline auth status` — that is where rows get written. This step is
about the **Lanyard account**, which is where the campaign runs and whose credits get spent.
They are unrelated, they belong to different people as often as not, and nothing links them.

Check `LANYARD_API_KEY` in the environment first. If it is set, resolve whose Lanyard account
it is before using it — this also reports the free allowance and credit balance that Step 5
and Step 9 both have to state:

```bash
python3 scripts/drive_load.py conference-config.json account
```

That command reports the **Lanyard** account only. `deepline auth status` reports the
Deepline workspace and says nothing about Lanyard; neither answers for the other.

**If an account is already there, the only question is WHICH EMAIL — ask exactly that.** A
saved key is not consent to use the account behind it: the campaign lands in that account and
the credits come out of it, and the person at the keyboard may not be the person the key
belongs to. But do not turn that into a discussion about keys or sign-in mechanics. Show the
email and offer two choices:

- *"Use `<the email the account command printed>`"*
- *"Use a different email"* → the sign-in below, which replaces the stored key

That is the whole question. Nobody needs to know there is an API key involved, or that
choosing the second option re-runs an auth flow — they picked an email, and the rest is
plumbing. One click either way, and never silently: the failure it prevents is a shared
machine, or a handed-over laptop, quietly spending somebody else's credits.

A live key prints the account, its credit balance and its free dossiers per campaign. A dead
one prints `401 unauthorized: Invalid or revoked API key` — say plainly that the saved key is
no longer valid and sign in again rather than retrying it.

**A `403` whose body is not JSON is NOT a bad key**, however much it looks like one. The
service sits behind an edge that refuses some clients before the request reaches the API —
measured, Python's default user agent gets exactly that. The client here sends a named agent
for that reason, and reports such a response as an edge refusal rather than an auth failure.
If you see one, check egress and proxies; do not send the person back through sign-in.

If there is no account yet, sign in. It is the same login as the website — an email and a
one-time code, no password. **YOU run both calls. Do not hand them a script, do not send them
to a terminal, and do not write a sign-in helper** — the whole thing is two requests and a
code they read off their phone.

Say what is about to happen, then send the code:

```bash
curl -s -X POST https://lanyard.redlinegrowth.com/api/public/v1/auth/start \
  -H 'content-type: application/json' -d '{"email":"THEIR_EMAIL"}'
```

**Ask for the code on a dialogue card and let them type it in.** That is fine, and this
distinction matters more than anything else in this step:

- **The one-time code MAY be pasted into the conversation.** It expires in minutes, it works
  once, and after `auth/verify` redeems it there is nothing left to steal. Treating it like a
  credential — making somebody open a terminal to type a few digits — buys no safety and
  costs them the thread they were in. Do not state how many digits to expect and do not check
  the length; take whatever arrived.
- **The API KEY must never be.** It is long-lived, it spends money, and it is shown exactly
  once. Never printed, never pasted, never put in a command argument (arguments are visible
  in `ps` to every process on the machine), and never read back into the conversation.

So redeem the code yourself, and send the key **straight to disk without it passing through
your own output**:

```bash
curl -s -X POST https://lanyard.redlinegrowth.com/api/public/v1/auth/verify \
  -H 'content-type: application/json' \
  -d '{"email":"THEIR_EMAIL","code":"THE_CODE","label":"Deepline skill"}' \
 | python3 -c 'import json,sys,os;k=json.load(sys.stdin)["api_key"];fd=os.open(os.path.expanduser("~/.lanyard-env"),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600);os.write(fd,("LANYARD_API_KEY="+k+"\n").encode());os.close(fd);print("key stored")'
```

That prints `key stored` and nothing else. Point the config's `key_file` at that path, or
export the variable, then confirm with the `account` command — which shows the email and
never the key.

If the code is rejected, say so plainly — they expire quickly — and offer a fresh one. Do not
retry the same code.

## Step 2 — Which company is going

**Ask this before the conference.** Everything downstream is scored against this company —
the rubric, the ranking, every dossier's value prop — so it is the frame the rest of the
answers sit inside, and asking it first is what makes "who is worth meeting" a question with
a subject.

**Offer a domain; never assume one.** You have hints, and hints are options on a card, not
answers:

- **The domain of the Lanyard account's email**, when it is not a mailbox provider. Strip any
  plus-addressing first — `someone+20260922@acme.com` is an address at `acme.com`, and the
  tag after the `+` is not part of anything. Offer `acme.com`.
- **The Deepline workspace name** (or `businessDomain` from `deepline auth status --json`),
  when it suggests a company.
- **"A different company — let me type it"**, always, because the two above are guesses.

The card asks *"Which company is going to this conference?"*, lists what you found, and lets
them type anything else. One click in the common case.

**An email domain is a hint, not a fact, and the ways it is wrong are ordinary.** Agencies and
consultancies run conferences for clients. Contractors carry their own address. Somebody
signed up with a personal account and is going on behalf of their employer. A free-mail
address — `gmail.com`, `outlook.com` and the rest — says nothing at all about an employer and
must never be offered as one. Silently adopting the email's domain produces a campaign
calibrated against the wrong company, and every score in it is then wrong in a way no output
reveals.

## Step 3 — Which conference, and confirm the edition before anything else

**Ask one thing: which conference.** On a card, like everything else — the answer arrives
through its free-text box, because the answer space is every event in the world and no list
can cover it. A name is enough; a city or year helps when the name alone is ambiguous.

Then look it up immediately, before asking anything else:

```bash
python3 scripts/drive_load.py conference-config.json run --conference "NAME" --city "CITY" --year YYYY
```

Without `--yes` this stops after showing the match. **Put the match in front of them as a
card they can click, not as a paragraph to read** — options roughly:

- *"Yes, that's the one"*
- *"Right event, wrong edition"* → ask for the city or year and look it up again
- *"Not that event"* → resolve it by URL, below

**When the name resolves to the wrong event, hand Lanyard the event's own page.** Do not ask
them to go and find it — search for it yourself, say which page you are about to use, and look
it up again with `--conference-url`:

```bash
python3 scripts/drive_load.py conference-config.json run --conference "NAME" \
        --conference-url "https://www.example.com/the-event"
```

Lanyard resolves the edition from the page, and it is decisive: measured live, `SaaStr Annual`
resolves to the September event in San Mateo while `https://www.saastrannual.com/` resolves to
SaaStr AI Annual in May in the Bay Area. Two different real events, one name, and only the URL
separates them. Ask them for the link only when the search does not settle it — and if the URL
still resolves to something they do not recognise, say so plainly rather than proceeding.

Show the match as one line inside the question: name, dates, location, and the service's own
confidence.

**Halt here (`other`).** And confirm the EDITION before collecting anything else, because the
lookup costs nothing and a wrong event makes every later answer worthless. The failure this
prevents is the one nobody catches: the wrong edition returns a complete, confident, plausible
list of people who will not be there.

## Step 4 — The rest of the definition, as a conversation

**This is a dialogue, not a form.** The instinct is to save the person's time by asking for
everything at once, and it backfires: a numbered list of five questions is a form, and a form
gets skimmed, half-answered, or abandoned. Watched on a real run — the skill emitted five
numbered items in one message and the person's reaction was that it was not finished.

**So every one of these is a dialogue card.** The closed ones carry options; the open ones
carry the question and rely on the card's own free-text box. Concretely:

**What a good person to meet looks like** — the API takes `goals` as
`{categories[], freeform}`, and **the categories are a closed set**, so ask them as a
multi-select: clients, partners, investors, hires. Then ask once, as free text, for the
specifics that sharpen it — "revenue leaders at mid-market SaaS evaluating gifting" ranks very
differently from "anyone senior", and that sentence is the rubric.

**Who is going from your side** — options: *"just me"*, *"nobody from our side"*, *"let me
list them"*. Only the third needs typing.

**Do you already have an attendee list?** Ask it, because it changes the quality of everything
downstream and almost nobody volunteers it. Options:

- *"Yes, this year's"* → ask for the file path
- *"Yes, last year's"* → ask for the file path, and label it as last year's
- *"No — find them yourself"* → Lanyard finds the attendees for us. This is the default and
  it works
- *"No — but build a seed list first"* → only if they ask for it. Deepline can assemble a
  seed CSV from public LinkedIn activity around the event, which Lanyard then scores on top
  of its own search. Find the conference's posts with `harvestapi_search_posts` (`search`:
  the event hashtag or name, `postedLimit` to bound it), then pull who engaged with each post
  via `harvestapi_get_post_reactions` and `harvestapi_get_post_comments` (`post`: the post
  URL). Each is priced per page at 0.03 Deepline credits per `deepline tools describe` — check
  it live and state the page count before running. A LinkedIn *event* page has no native
  tool: find an actor with `apify_list_store_actors` (free) and run it with
  `apify_run_actor_sync` (priced from usage). Dedupe on profile URL, write
  `name,title,company,linkedin_url` to a CSV in the run directory, point
  `attendee_list_file` at it, and set `attendee_list_year` to `this year`. **Say what it is:
  people who engaged with the event online, not registrants** — Lanyard's per-contact
  attendance confidence is still what to filter on. The pattern is spelled out in the
  `conference-attendee-list` skill where it is installed.

A list of 500 or fewer needs **no upload anywhere**: it is sent inline with the campaign, and
the service still searches for more on top of it. Point `attendee_list_file` at a CSV or TSV
(export a spreadsheet first) and `attendee_list_year` at `this year` or a year. A name column
is required; title, company, email, LinkedIn and phone are used when present.

**Last year's list is a different claim from this year's, and the skill must not blur them.**
It is real evidence that somebody may come again; it is not evidence that they are coming. So
the year is told to the scoring, and every contact still carries the service's own
`Attendance confidence`, `Attendance evidence` and `Attendance year` — which is where a
segment should look before anybody books a flight.

Report what the list actually parsed: rows read, attendees seeded, rows **dropped** for having
no name, and anything truncated past 500. A list that half-failed to parse looks exactly like
a small conference.

**How many dossiers to ask for** — do NOT ask. It is defaulted, the account's real allowance
is already known from Step 1, and both appear in the plan at Step 5 where a number can be
changed. Asking for a number whose ceiling the person cannot see is a worse question than no
question.

Ask the closed ones together in one interaction — they are independent, so batching them costs
nothing and clicking three options is not a form. Ask the free-text specifics on their own,
after, where the answer has room to breathe.

Write the answers into the working config (Step 0). The config holds no credentials and must
never be given any.

## Step 5 — The plan, and one gate

**First, price the build without doing it.** The dry run creates nothing and prints exactly
which columns would be created and which already exist and would be adopted, so the plan can
state real numbers rather than "some columns":

```bash
python3 scripts/build_conference_writer.py conference-config.json --dry-run
```

Then show all of it in one message, and stop:

- **The event** — name, dates, location, as verified.
- **The campaign** — how many dossiers are being asked for, and what the account's free
  allowance actually is, read from `/me`. If the allowance is lower than the ask, say so
  before the run, not after: *"your account covers N full dossiers on this campaign; the rest
  come back ranked and locked."*
- **The workspace** — which Deepline workspace, whether the two tables need creating or are
  already there from a previous conference, and how many columns would be created versus
  adopted (the dry run just counted them). On anything but the first run the new-column count
  is usually zero, and saying so is the difference between a plan and a formality.
- **The writes** — one row in `storage.conference_attendees` per attendee with a dossier; one
  row in `storage.conference_companies` per company domain, with the attendee linked to it.
- **What is never touched** — no message is drafted or sent, nothing goes to a CRM, no
  populated column is cleared, no row is deleted.

**Say how long it takes, and what will exist afterwards.** Before the halt, not after —
somebody agreeing to wait needs to know they are waiting:

> *"This usually takes 10 to 20 minutes, and a big event with hundreds of candidates can run
> longer. When it finishes, the ranked attendees land in your
> Deepline customer DB as rows — each with their tier and score, how confident we are they
> are attending and the evidence for it, a dossier headline and summary, a summary of their
> company, their buying signals, conversation openers and a value prop — and each linked to
> their company where we can identify it. Every one of those is a column you can filter and
> segment on."*

Name the data points rather than saying "enriched". A person who is told "we will enrich them"
has agreed to nothing in particular; a person told they are getting tier, score, attendance
evidence, openers and a value prop can tell whether the wait was worth it. Quote the range
rather than a single number — measured runs have landed at about eleven minutes on a
mid-sized event and past forty on a large one, and a promise of "15 minutes" turns the second
of those into a failure when it is just a bigger conference.

**Halt here for both `spend-approval` and `write-approval`.** One gate, three things, asked
once: the campaign is the spend, and the tables and the rows are the write.

**Nothing has been created in their workspace at this point, and that is the whole reason
this step comes before the build.** An earlier version built first and asked afterwards,
which meant roughly two dozen columns appeared in somebody's workspace before they had agreed
to anything — and the gate that was supposed to cover "the write" only ever mentioned the
records. A plan describing writes that already happened is not a plan.

## Step 6 — Build the tables, once — after the yes

**Only now, and only because they said yes at Step 5.** This step creates tables in their
customer DB. Never run it before the gate.

**And it is built ONCE PER WORKSPACE, not once per conference — usually it does nothing at
all.** The tables are entirely generic: the event, the campaign id and the dossier arrive as
row values, so the same two tables serve every conference this workspace will ever run. Their
names are constants in `scripts/conference_lib.py`, and there is no config field for them,
because a field invites naming them after the first conference.

The writer's config lives at a stable workspace-keyed path
(`~/.deepline-conference-writer/<workspace id>/` by default), **not beside the campaign
config**. The campaign config is per run; the writer is not.

So on the second and every later conference, this step prints that the tables already exist
and moves on. Say so plainly — *"the tables are already in your customer DB from last time;
nothing new is being created"*.

**Why tables in the customer DB and not a CSV.** The top-up is the whole point — the same
destination has to still be there in three weeks when somebody unlocks forty more dossiers,
without this conversation, and a re-run has to update rows rather than produce a second file
to reconcile. An upsert keyed on the attendee is that; a CSV is not. The customer DB is also
where Deepline plays read and write, so the next enrichment pass can start from these rows.

The dry run already ran at Step 5 and its numbers are what they agreed to, so this is the real
one:

```bash
python3 scripts/build_conference_writer.py conference-config.json
```

It checks the Deepline login resolves to the config's `workspace_id` and refuses otherwise,
runs `CREATE TABLE IF NOT EXISTS` then `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for every
column, reads `information_schema` back and refuses to report success if a column is still
missing, and writes `writer-config.json`. If the dry run's counts have changed since the plan —
somebody added or retyped a column meanwhile — say so rather than quietly building something
they did not agree to.

**The two traps the build exists to survive:**

- **`deepline db query` writes only to schema-qualified `storage.*` tables.** An unqualified
  `CREATE TABLE conference_attendees` is refused. The names here are already qualified.
- **A column that exists at a different type is adopted, not recreated.** The build names the
  mismatch, and the driver validates against the column's real type, so a value that does not
  fit is dropped and named rather than failing the whole batch.

Re-running the build is a no-op over what already exists.

## Step 7 — Run it, and say what it is doing

Re-run the Step 3 command with `--yes`. The campaign starts and the script polls it, printing
each stage as it changes: researching, discovering, ranking, enriching, dossiers.

**Report a stage when it CHANGES, and otherwise say nothing.** The script already polls; you
do not need to. Watched on a real run: roughly twenty-five near-identical "still ranking"
messages went by, none of which told anybody anything, and the cumulative effect was to make
a service that was working steadily look stuck. Silence between milestones is correct — a
person who has been told it takes a while does not need proof of life every forty seconds.

If you do want to check mid-run, `status` gives the real counts in one call. Do not hand-roll
polling loops, and do not read "the same stage twice" as a fault: discovery and ranking are
long passes over hundreds of people, and a stage message that has not changed usually means
work is being saved underneath it, not that anything is wrong.

**On how long: say it varies, and do not quote a tight number.** The service's published
range is 5 to 20 minutes and it depends on the size of the event — a big conference with
several hundred candidates can run longer, and that is the system working rather than
failing. One measured run finished in about eleven minutes; another, on a larger event, ran
past forty. Tell them it is usually 10 to 20 minutes and that a large event can take longer,
so that a long run is something they were told about rather than a broken promise.

**The campaign id is written to `campaigns.jsonl` before polling begins.** If the session dies
mid-poll, nothing is lost — the campaign keeps running on Lanyard's side and Step 8 picks it
up from the id.

**Settle only on `complete` or `failed`.** Never on a count: the dossier count moves while the
last dossiers are still being written, so a run that looks finished by its numbers is not. If
it fails, report the reason in plain words and offer to retry. Never present a partial result
as a complete one.

## Step 8 — Load everyone who has a dossier

The run command does this automatically when the campaign completes. To do it separately — or
at any later point — it is one command, and it is the same command every time:

```bash
python3 scripts/drive_load.py conference-config.json load --campaign <campaign id>
```

It re-reads every contact, takes everything carrying a dossier, subtracts what the ledger
already settled, and writes the difference in batches. Every verdict is appended to the ledger
the moment it settles, and **only a written row settles** — the upsert `RETURNING`s the key of
every row it wrote, and an attendee whose key is not in that list is not counted. A failure
stays in the work set so the next run retries it untouched. Do not "fix" a transient failure before retrying it.

## Step 8b — Report what actually landed, and what did not

Verify against the customer DB rather than trusting the load's own count:

```bash
deepline db query --sql "select count(*) as attendees, count(company_domain) as linked from storage.conference_attendees where campaign_id = '<campaign id>'" --json
```

Then report, in this order:

1. **What is now in the customer DB** — how many attendee rows landed, how many are linked to
   their company, and the data points each one carries. Not "5 enriched": the person agreed to
   a specific list of columns at Step 5, and this is where they find out they got them.
2. **The people**, each with the one line that says why they are worth meeting.
3. **What was dropped and why** — every attendee who could not be written, by name, with the
   reason. An attendee with neither a LinkedIn URL nor an email cannot be matched on anything;
   say so rather than letting them vanish into a count.
4. **Which edition the evidence is about — the whole pool first, then the written few.**
   The campaign reports its own breakdown across everything it found ("144 people: 70
   this_year, 54 last_year, 19 prior"), and the loader adds the split across the ones just
   written. Lead with the pool: it says what the search turned up, where the written split
   says as much about the size of the free allowance. Present both as what they are — a
   provenance label most attendee sources do not give you at all, and the thing that lets
   them filter to people evidenced against the upcoming event. The ones from a previous
   edition are regulars worth knowing about, not padding.
5. **What is still locked, by tier** — the ranked attendees with no dossier yet. The loader
   prints this from the contacts themselves, so it agrees exactly with what an unlock would
   match. (When the campaign publishes its own `locked` block that carries tiers too; a
   locally counted fallback cannot, and must never be presented as a tier breakdown.)
6. **The unlock offer** — see Step 9. This is the question they will have anyway.
7. **One link, one next step, and an open door.** End with
   `lanyard.redlinegrowth.com/campaign/<campaign id>` — the signed-in page where the dossiers
   are — then tell them they can unlock more from there whenever they like, today or in a
   month, and that coming back and asking is all it takes to get the new ones into their
   customer DB. Say plainly that a later session needs nothing from them: not the id, not this
   conversation, not anything on this machine.

   **Exactly one link.** An ending that offers a page, a payment link and a command makes
   somebody choose between three things before they have read anything. There is one thing
   worth doing next: open it, read what came back, unlock more if it earns it.

   **And not `share_url`.** It looks like the obvious field and is a different thing: a
   `/claim?t=<token>` link whose token grants access to whoever holds it. Right for handing
   results to a colleague with no account; wrong as "your results", because it is both the
   wrong page and a quiet act of sharing nobody asked for.

## Step 9 — Unlocking more, which normally happens in Lanyard

Everything ranked but not enriched is unlockable. **The normal path is that they unlock on
the campaign page** — they are already there reading dossiers, the tiers and prices are in
front of them, and the decision is better made looking at the actual people than at a count
in a terminal. The load has already told them this and asked them to say when they have.

When they do, run the ordinary `load` again. That is the whole flow, and it is the same
command as the first load.

**The rest of this step is for when somebody asks to unlock without leaving the
conversation.** It is a real capability, not the default — do not lead with it.

**Suggest a default rather than asking an open question.** "Do you want to unlock any?" makes
a person do arithmetic against a tier breakdown; a suggestion makes them agree or adjust. The
loader's heuristic: the S tier alone when that is between 5 and 25 people, S and A together
when S alone is thinner than that, and a capped top 25 when S alone is already more than
anybody reads in one sitting. **Say it is a heuristic** — it is a batch size, not a view on
who matters, and the tiers are the service's scoring rather than the person's judgment.

Price it before spending — the quote is free and it is the number they are agreeing to:

```bash
python3 scripts/drive_load.py conference-config.json unlock --tier S
```

That **prices only**. It prints how many locked contacts match, what they cost, and what the
account holds. Spending needs `--confirm-spend` on top, and that flag must never be passed
without an explicit yes.

**Halt here (`spend-approval`).** State three things and stop: how many, how much, and the
balance. *"12 S-tier attendees are still locked. That is 60 credits and the account holds 0."*

**A shortfall is not an error, and with a free account it is the normal case** — a new
account holds 0 credits, so the first unlock anybody attempts cannot be paid for. When the
balance cannot cover it the quote carries a `payment_url`. Put the number and that link in
front of the person and **stop**:

- Never attempt a payment, and never follow the link yourself. Money moves in a browser where
  somebody can see what they are buying.
- Never retry a shortfall. It is a price, not a transient failure.

After a successful unlock the service may report `dossiers_pending` — dossiers still being
written. Those contacts have **no dossier yet**, so a load right now skips them. Say so, and
run the load again once they finish rather than reporting a short write count.

Then write them with the ordinary load. There is no special path: the dossiers now exist, so
the same re-read picks up exactly the new ones.

## Step 10 — The top-up, weeks later, from a session that knows nothing

**Assume the next session has nothing.** No config, no campaign id, no memory of this
conversation, and the folder this run used long since tidied away. That is the normal case:
somebody unlocks a few more dossiers in Lanyard in a fortnight and asks an agent to put them
in the customer DB. It has to work from that, or the top-up is a promise rather than a feature.

It does, because nothing it needs is per-campaign:

- **The writer** is two workspace-level tables, found by name, and its config lives at
  `~/.deepline-conference-writer/<workspace id>/`, found from `deepline auth status --json`.
- **A workspace-level config** sits beside it, written by the build. It carries the
  workspace, whether companies are linked, and where the key is — and nothing about any
  conference. Point `drive_load.py` at that file. A stale path from an old note also works:
  when the config is missing the driver asks Deepline which workspace this is and reads the
  writer's own config instead, saying so.
- **The campaign** is found from the Lanyard account. `campaigns` lists them; `--match` picks
  one by phrase.
- **The ledger** lives beside the writer too, keyed by campaign id, so a later session knows
  which attendees are already in and writes only the new ones.

Either this skill unlocked more at Step 9, or they unlocked on the campaign page themselves —
possibly on another device, possibly last week. Nothing tells the skill which, and it does not
need to know:

```bash
python3 scripts/drive_load.py conference-config.json load --campaign <campaign id>
```

The same command. It re-reads the campaign, finds the dossiers that now exist, and writes only
those. Attendees already in the table are not rewritten. If nothing was unlocked, it writes
nothing and says so.

To look before loading:

```bash
python3 scripts/drive_load.py conference-config.json status --campaign <campaign id>
```

**Ask for it by name rather than by id.** Somebody coming back says "the SaaStr one", not a
UUID:

```bash
python3 scripts/drive_load.py ~/.deepline-conference-writer/<workspace id>/writer-config.json load --match "saastr"
```

Every word of the phrase has to appear in the campaign's conference, edition, city, label or
id. That is deliberately strict rather than fuzzy: a loose matcher that guessed which
conference somebody meant would write the wrong event's people into their customer DB, and the
ids are opaque enough that nobody would notice. Two matches, or none, and it lists what it
found and refuses.

**Or list them, when even the name is vague:**

```bash
python3 scripts/drive_load.py conference-config.json campaigns
```

That lists every campaign on the account, newest first, with its conference, how many
attendees were found, **how many have this year's evidence**, how many dossiers exist, how
many are still locked and what unlocking them all would cost — enough to decide which campaign
is worth going back to without fetching anybody's contacts. With exactly one campaign the load
will use it without being told; with several it refuses to choose and asks which. Choosing a campaign for somebody means choosing whose people land in
their customer DB, and the ids are opaque enough that a wrong guess would not be noticed.

## Representative output

### The load report, printed in the session

Real output from a live run against a real conference, on a free account — 144 attendees
found. The conference and the campaign id are left out; the numbers are as they printed.

```
reading campaign <campaign id>
  status complete · 144 contacts known

== the plan ==
  5 with a dossier and not yet written
    linked_linkedin        5
    skipped: ranked_only   139

  enrichment allowed: 5 of 25 requested (source: campaign)
  139 more are ranked and waiting without a dossier — by tier: 12 S, 15 A, 18 B, 73 C, 21 F

== writing ==
  batch 1: 5 attendees

== what is now in storage.conference_attendees ==
  5 attendee record(s) written
  5 of them linked to their company (5 company row(s) upserted)
  each carries: tier, score, rank, attendance confidence and evidence, the dossier
  headline and summary, their company summary, buying signals, conversation
  openers and a value prop — every one a column you can filter on

== still locked ==
  139 ranked attendee(s) have no dossier yet: 12 S, 15 A, 18 B, 73 C, 21 F

  unlocking would cost (5 credits each, account holds 0):
    -> tier S              12 contacts    60 credits  (more than the balance)
       tiers S and A       27 contacts   135 credits  (more than the balance)
       the top 25          25 contacts   125 credits  (more than the balance)
       everything locked  139 contacts   695 credits  (more than the balance)

  suggested: tier S — a batch big enough to be worth reviewing and small
  enough to read in one sitting. A heuristic, not a view on who matters.

  price it (spends nothing):
    python3 drive_load.py <config> unlock --tier S
  the balance does not cover it — the quote prints a link to top up.
```

Run it again with nothing unlocked and it writes nothing, says so, and still shows the offer —
because that is the run somebody checking back is on:

```
Nothing new to write — everything with a dossier is already in the customer DB.

== still locked ==
  139 ranked attendee(s) have no dossier yet: 12 S, 15 A, ...
```

### The attendee row it leaves in the customer DB

The shape of one row, read back with `deepline db query` after a load. **The person, their
company and every line written about them are invented here** — the run was real and the
fields are exactly the ones it filled, but a real attendee's contact details and a dossier
on how to sell to them are not ours to publish. Expect values of this kind, not these values.

| Field | Value |
|---|---|
| Name / Title / Company | Priya Raman · CMO · Vantage Loop |
| Email / LinkedIn URL | priya@vantageloop.example · linkedin.com/in/<handle> |
| Conference / start / location | <conference> · 2026-10-12 · Nashville, USA |
| Attendee tier / score / rank | S · 88 · 5 |
| Attendance confidence | confirmed |
| Attendance evidence | Listed as a speaker on the published agenda for the 2026 edition. |
| Attendance source | vantageloop.example/the-agenda |
| Dossier state | enriched |
| Dossier headline | Scaling high-touch patient access through precision B2B demand generation |
| Dossier summary | Priya Raman is the Chief Marketing Officer at Vantage Loop, with two decades in… |
| Their company | Vantage Loop provides AI-powered patient access and revenue-cycle software… |
| Buying signals | A recent push into AI-driven workflow automation suggests receptivity to… |
| Value prop | For a CMO navigating a complex healthcare buying committee, <your product> offers… |
| Conference campaign id | <campaign id> |

Linked to the `storage.conference_companies` row for that company's domain by
`company_domain`: joining the two tables on it returns this person under that company and
nobody else.

## What this skill does not claim

  - A ranked attendee is a well-evidenced belief, not a confirmed registration**, and this is
    the single most important thing to read before booking a flight. No attendee product can
    confirm a registration it cannot see; this one shows its working instead. Every record
    carries `Attendance year` (a documented enum: `this_year`, `last_year`, `prior`), the
    confidence, and the evidence sentence behind it, and the campaign reports the split across
    everything it found — two live campaigns turned up 70 of 144 and 120 of 173 with this-year
    evidence. So the provenance travels with each record and the filter is safe to write. A
    `likely` is not a `confirmed`. Apply the filter before treating the list as people who will
    be in the building.
  - No attendee list is complete, and this one does not claim to be.** The attendees are the
    ones Lanyard finds, plus any you supply. A private event app is not read. "144 attendees
    found" is what was found, not who is going.
  - No conversion, meeting or reply rate is claimed anywhere**, and no benchmark for one
    exists in this package.
  - The scoring rubric is generated per campaign from your own goals**, so two runs with
    differently worded goals rank the same people differently and a score is not comparable
    across campaigns. A vague sentence of goals produces a vaguely ranked list: measured, a run
    asking for "marketing, RevOps and sales leaders" returned two investors in its top five —
    plausible people to meet at that event, but not the roles that were asked for. Read the top
    of the list before acting on it, and sharpen the goals if it is not what you meant.
  - A corrected company replaces the link; the old company row stays.** The link is the
    attendee's `company_domain`, so a rewrite with a different domain moves them. Nothing
    deletes rows, so the earlier company row remains in `storage.conference_companies` with no
    attendee pointing at it.
  - An attendee with no usable email cannot be linked to a company.** Contacts do not carry a
    company domain, so the domain is derived from the email address. An attendee whose only
    address is at a mailbox provider is written unlinked by design, and an attendee with no email
    at all cannot be linked to anything.
  - The dossier field names are a moving target.** The shape measured here shares exactly one
    key with the shape the service's own documentation describes, so every read scans both. If
    the service changes again, columns go blank rather than wrong — but they do go blank.

## What good looks like

- The service is introduced in plain words BEFORE the first question. Nobody is asked for an
  email by a product they have never heard of.
- Each step says what it is about to do before doing it. Nobody has to infer what a question
  is for, or what happens after they answer it.
- Nothing is created in their workspace until they have approved a plan that names it.
- The company going is established FIRST, as a click on a guess rather than an empty prompt —
  and never silently adopted from an email address.
- The conference is asked for next, on its own, and the EDITION is confirmed — as a click, not
  a paragraph — before anything else is collected.
- **Every** question arrives as a dialogue card, the open ones included. Nothing is asked as
  prose in the conversation.
- Nobody is handed a numbered list of five questions. A form gets skimmed, half-answered or
  abandoned, and reads as unfinished work.
- Nothing is asked whose answer is already prescribed, defaulted, or visible in the plan.
- An existing account is offered as an email to keep or change — not as a question about
  keys, sign-ins or authentication. Nobody needs to know an API key exists.
- Signing in is two requests and a code typed into a card. Nobody is sent to a terminal, and
  no sign-in helper is written for them.
- They are asked whether they already have an attendee list, because they will not offer it.
- They are told it takes 10 to 15 minutes, and told which columns they are getting, BEFORE
  agreeing to wait — not after.
- The closing report says what landed in the customer DB, not that something was "enriched".
- The unlock offer arrives with a suggested batch and a price, not as an open question.
- A zero balance produces a link, never an attempted spend and never a retry.
- The free allowance is stated **before** the campaign runs, with the number of dossiers
  actually coming.
- Every attendee with a dossier is in the customer DB, linked to their company where a domain
  exists.
- Every attendee who could not be written is named, with the reason.
- A value that would have been invisible to filters is dropped and reported, never written.
- The count is verified with a query against the table, not read off the loader's own report.
- Running `load` twice in a row writes nothing the second time, and says so. An attendee
  nothing can match keeps being reported each run rather than settling — that is deliberate,
  since they may acquire a profile later, but it means "nothing to write" and "nothing left"
  are not the same sentence.
- Running `load` after someone unlocks forty more writes exactly forty.

## Rules

1. **Ask every question on a dialogue card.** No exceptions: closed questions carry options,
   open ones use the card's free-text box. A question typed into the conversation, or a
   numbered list of them, is the failure mode — not the efficient version of it.
2. **Introduce Lanyard before asking for anything, and say what the next few minutes hold.**
   An unexplained third party asking for an email is where a reasonable person stops.
3. **Narrate before acting, at every step and not only at the gates.** One sentence on what
   you are about to do and why the question is being asked now. Being walked through
   something and being interrogated by it differ by about a line each time.
4. **Create nothing in their workspace before the plan is approved.** Tables and columns
   are writes; a plan that describes writes which already happened is not a plan.
5. **Establish the company before the conference, and never infer it from an email address.**
   Offer the email's domain (plus-addressing stripped) as an option and let them correct it.
   An agency, a contractor or a personal address makes that guess wrong, and a campaign
   calibrated against the wrong company is wrong in every score without saying so.
6. **Never invent an attendee, a date, an email or a line of a dossier.** Everything reported
   comes from a response. If a field is empty, it is empty.
7. **Confirm the conference edition before starting a campaign.** Always. It is the one error
   that produces a confident, complete, wrong answer. When the name resolves to the wrong
   event, look the event up yourself and re-run the lookup with `--conference-url`; Lanyard
   resolves the edition from the page. Do not send someone away to find a link you can find.
8. **State the free allowance up front, once, with the real number.** Never imply more is
   free than is.
9. **Never claim a campaign is done before its status says `complete`.** Not on a stage, not
   on a count.
10. **The key is never asked for in conversation, never printed, and never passed as an
   argument.** It lives in the environment or in a file the config names. **The one-time code
   is not the key**: it may be typed into a card, because it expires in minutes and works
   once. Never send somebody to a terminal or write them a script to hand over an OTP — that
   buys no safety and costs them the thread they were in.
11. **Write only attendees who have a dossier.** A ranked contact without one is not a thin
   record to be filled in later; it is a contact whose research has not been paid for.
12. **Validate every value against its column's real type before writing it.** A value the type
   cannot parse fails the whole batch statement. Drop it and name it.
13. **Never send a blank as an empty string.** The upsert keeps the old value only for NULL
   (`COALESCE`); an empty string wins and clears a populated column.
14. **Distinguish every reason a contact was not written** — `ranked_only`, `queued`, `failed`,
   `unranked`, `already_written`, `unwritable`. Collapsing them makes every rate meaningless.
15. **Only a row the upsert RETURNed settles in the ledger.** A failure stays in the work set. Do not
    repair a transient failure before retrying it.
16. **The top-up is the same command as the load.** Never build a second path for it, and
    never ask the person to tell you what they unlocked — they should not have to know, and
    they will be wrong.
17. **Never draft or send a message, and never enrol anyone in a sequence.** This skill
    produces records. What happens next is somebody else's decision.
18. **Write every run file to `~/.deepline-conference-writer/<workspace id>/runs/<date>/`, and
    never inside a git repository.** Not `runs/`, not `conference-runs/`, not a dot-prefixed
    version of either — three cold runs each invented one inside the repo the session started
    in, and that output carries real email addresses, the path the key was written to, and
    live share tokens. Hiding it from `ls` does not hide it from `git add -A`.

## Worked example

Someone says: *"Get me the people worth meeting at INBOUND."*

**Step 0.** Before anything else, say what this is: *"This uses Lanyard, a service that finds
who is going to a conference, scores them against what you are looking for and writes a short
dossier on the best ones. Free account, a handful of full dossiers per conference, and the
results land in your Deepline customer DB."* Then `deepline auth status --json` names the
workspace and the `information_schema` read answers, so: *"This writes attendee and company
rows into two tables in <workspace>'s customer DB, creating them the first time. It sends
nothing to anyone."*

**Step 1.** There is already an account, and it resolves to `someone@example.com` with 0
credits and 5 free dossiers per campaign. The card asks one thing — *use
`someone@example.com`* / *use a different email* — and they click the first. Not assumed: the
credits would have come out of that account. Keys are never mentioned; they chose an email.

**Step 2.** A card asks which company is going. The account email is
`someone+20260922@example.com`, so `example.com` is offered with the plus-tag stripped,
alongside the Deepline workspace name and *"a different company — let me type it"*. They are
running this for a client, so they click the third and type the client's domain. Had it been
assumed from the address, every score in the campaign would have been calibrated against the
wrong company.

**Step 3.** One card: which conference. They type *"INBOUND"* into its free-text box. The lookup runs immediately
and comes back *INBOUND 2026 · 3–5 September 2026 · San Francisco, CA · inbound.com ·
confidence high*, put to them as a choice — *that's the one* / *right event, wrong edition* /
*not that event*. **Halt.** They click the first. Nothing else has been asked yet, so if they
had clicked the third, nothing would have been wasted.

**Step 4.** Three cards in one interaction: what a good person to meet looks like (*clients*, from clients / partners /
investors / hires); who is going (*let me list them* → a CRO and a sales manager); and whether
they have an attendee list (*yes, last year's* → a CSV path). Then one free-text follow-up for
the specifics: *"revenue leaders at mid-market SaaS companies evaluating gifting."*

The list reads back: *"read 412 rows, seeded 400 attendees, dropped 12 rows with no name,
truncated 0 — labelled as last year's."* Said out loud, because 12 silently dropped rows is
how a list half-fails.

**Step 5.** The dry run counts it first, creating nothing: of the 38 columns in the plan —
32 on attendees, 6 on companies — neither table exists yet, so all 38 would be created. Then
the plan, including how long and what they get: *"about 10 to 15 minutes, and
you will end up with ranked attendees in your Deepline customer DB carrying tier, score, attendance
evidence, a dossier headline and summary, their company summary, buying signals, conversation
openers and a value prop."* Asking for 25 dossiers; `/me` says the account's free allowance is
5 per campaign, so five are coming and the rest will be ranked and locked. Writing into
`<workspace>`, creating two tables. One attendee row per attendee with a
dossier, plus a company row wherever a domain is known. No message is drafted or sent.
**Halt.** They say go. Nothing exists in their workspace yet.

**Step 6.** Only now does anything get built: two tables, 38 columns, read back from
`information_schema` before the build reports success.

**Step 7.** The campaign starts. Stages reported as they change. It completes in about eleven
minutes: 166 attendees found, 5 enriched, 5 dossiers.

**Step 8.** The load writes 4 people and 3 companies. The fifth attendee has neither a
LinkedIn URL nor an email.

**Step 8b.** Verified with a count query: 4 attendee rows carry the campaign id. Reported: the four
people with their one-line reasons; the fifth named, with *"no LinkedIn URL and no email —
nothing can match them"*; the share link; and *"161 more are ranked and waiting, 159 of them
simply never enriched — unlocking happens in the browser."* Then the top-up command, spelled out.

Then the offer, straight from the loader: *"12 S-tier attendees are still locked. Unlocking
them costs 60 credits and the account holds 0 — here is the link to top up."* One number, one
link, nothing attempted.

**Two days later** they say: *"I unlocked the S and A tiers, add them."*

**Step 10.** The same command, nothing else asked. It re-reads the campaign and finds 26
contacts that now carry a dossier and are not in the ledger as written. Twenty-five have a
usable identifier and are written, along with 11 new company rows; the twenty-sixth is the
attendee from Step 8 who still has neither a LinkedIn URL nor an email, reported again by
name. The four written on the first run are not in the 26 at all — the ledger already settled
them — so nothing is rewritten and nothing is duplicated. It reports: *"25 written, 0 left
unsettled, 135 still locked."*

Nobody had to tell it which 26.
