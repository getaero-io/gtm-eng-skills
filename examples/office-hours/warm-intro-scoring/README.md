# Warm Intro Scoring

Office-hours example from May 7, 2026.

Rank mutual connections for warm introductions by usefulness, not by raw graph distance alone.

## Flow

1. Collect candidate introducers from LinkedIn, CRM owners, investors, customer references, and relationship graph providers.
2. Normalize every relationship into the same scoring payload.
3. Penalize stale, purely social, or one-way relationships.
4. Reward direct work history, recent interaction, shared deals, board/investor context, and seniority relevance.
5. Keep manual review in the loop before asking for an intro.

## Files

- `score-mutual-connections.ts` - composable TypeScript scoring helper.
