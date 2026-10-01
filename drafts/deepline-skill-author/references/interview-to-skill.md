# Interview → skill

For when there is no play, or the play has too little in it to convert. See §8 of
`references/play-to-skill.md` for what "too little" means.

No CLI needed to interview. You will need `deepline tools search` and `describe` (free) while drafting,
to name the real tool behind every paid step.

## What you will be asked

The order matters: purpose before mechanics, because mechanics without purpose produces a skill that
runs and helps nobody.

1. **The job.** What does someone want done, in their words? A skill is found by how people ask for
   it, so this becomes the description that decides when it triggers.
2. **The input.** What does the installer start with: a CSV of domains, a single company, a list of
   people? Name the fields.
3. **The steps.** What happens, in order, and what each step needs from the ones before it.
4. **The decisions.** Every threshold, band, tier or cutoff, and *why* that number. A skill that
   says "score highly" is not runnable; one that says "50 or more employees" is.
5. **The honest edges.** What should it refuse to guess at? What does it cost per row? What does it
   do when data is missing? "Returns nothing" is a real answer that should be stated, not padded.
6. **The boundary.** What should it NOT be used for? Naming the adjacent jobs is what stops the
   wrong skill being picked when somebody asks loosely.

Read `references/no-function-exists.md` *during* the interview: if someone says "and then merge the
duplicates" and nothing in the catalogue does that, it has to surface in the conversation.

## What comes out, and its limits

A complete `SKILL.md` whose `## What this skill does not claim` section names the interview as the
source of its logic.

That gap is not a formality. Interview-derived logic has **no ground truth anywhere**: it is your
stated intent, and nothing can check it against a play that already ran. A play-derived skill at least
has its thresholds traced to real code. This one does not, and the skill says so rather than implying a
check that never happened.

## Then lint it, and get it into the repo: the interview is not the last step

Back in `SKILL.md`, Steps 8 and 9: the answer sheet, `scripts/lint_skill.py --online`, and the two ways
to open the PR. Read the file end to end before that; on this route you are the only source its logic
ever had.
