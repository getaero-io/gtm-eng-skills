# Adversarial checklist

Before shipping, try to disprove the findings:
- Can the match be inside a longer word, boilerplate, negation, a hypothetical or a historical statement?
- Does the source describe a different company, a product being sold, or someone else's role?
- Did one provider fail more often for lost accounts?
- Were open roles counted as employees, or provider totals added together?
- Were phrases/aliases selected after looking at validation labels?
- Are the studies nested rather than independent?
- Was the feature known before scoring, not just before close?
- Do parent groups cross partitions, or multiple opportunities masquerade as independent accounts?
- Is the reported ratio feature prevalence or win rate? Are the denominators explicit?
- Are apparently significant results surviving a large search or repeated peeks?
- Is a large effect supported by one account, with wide uncertainty?
- Is a low-lift feature useful for ROI even if not prediction?
- Is a “no signal” actually no coverage or a schema mismatch?
- Did a ranking cap hide hundreds of candidate phrases or uncertain matches?
- Does a proposed disqualifier accidentally exclude the target's actual customers?
- Does the report imply a source is live when only its catalog entry was inspected?
- Did a local shortlist drop lineage or label a fuzzy name match a confirmed duplicate?
- Are fixed weights, universal lift ranges, or source hierarchies sneaking back into recommendations?

Do not weaken precision to get more results. Broaden source/query/alias coverage, retain a candidate queue, and validate separately. Document unresolved failures rather than marking them fixed.
