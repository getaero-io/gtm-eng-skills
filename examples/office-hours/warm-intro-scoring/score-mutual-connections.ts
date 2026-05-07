export type RelationshipSource =
  | "crm"
  | "linkedin"
  | "calendar"
  | "email"
  | "investor_graph"
  | "manual";

export type RelationshipEvidence = {
  source: RelationshipSource;
  introducerName: string;
  targetName: string;
  targetCompany: string;
  relationship: "worked_together" | "investor" | "customer" | "advisor" | "mutual_connection" | "unknown";
  lastInteractionDaysAgo?: number;
  sharedDeals?: number;
  introducerSeniority?: "exec" | "vp" | "director" | "manager" | "ic" | "unknown";
  notes?: string;
};

export type ScoredIntroPath = RelationshipEvidence & {
  score: number;
  tier: "strong" | "medium" | "weak";
  rationale: string[];
};

const SENIORITY_POINTS: Record<NonNullable<RelationshipEvidence["introducerSeniority"]>, number> = {
  exec: 18,
  vp: 14,
  director: 10,
  manager: 6,
  ic: 3,
  unknown: 0,
};

const RELATIONSHIP_POINTS: Record<RelationshipEvidence["relationship"], number> = {
  worked_together: 34,
  investor: 30,
  customer: 26,
  advisor: 22,
  mutual_connection: 12,
  unknown: 0,
};

export function scoreIntroPath(evidence: RelationshipEvidence): ScoredIntroPath {
  const rationale: string[] = [];
  let score = RELATIONSHIP_POINTS[evidence.relationship];

  if (score > 0) {
    rationale.push(`${evidence.relationship.replace("_", " ")} relationship`);
  }

  const seniority = evidence.introducerSeniority ?? "unknown";
  score += SENIORITY_POINTS[seniority];
  if (seniority !== "unknown") {
    rationale.push(`${seniority} introducer`);
  }

  if (typeof evidence.lastInteractionDaysAgo === "number") {
    if (evidence.lastInteractionDaysAgo <= 30) {
      score += 18;
      rationale.push("recent interaction");
    } else if (evidence.lastInteractionDaysAgo <= 180) {
      score += 10;
      rationale.push("fresh enough interaction");
    } else if (evidence.lastInteractionDaysAgo > 730) {
      score -= 12;
      rationale.push("stale relationship");
    }
  }

  if ((evidence.sharedDeals ?? 0) > 0) {
    score += Math.min(18, (evidence.sharedDeals ?? 0) * 6);
    rationale.push("shared deal history");
  }

  if (evidence.source === "manual" || evidence.source === "crm") {
    score += 8;
    rationale.push("first-party evidence");
  }

  const bounded = Math.max(0, Math.min(100, score));
  const tier = bounded >= 70 ? "strong" : bounded >= 45 ? "medium" : "weak";

  return {
    ...evidence,
    score: bounded,
    tier,
    rationale,
  };
}

export function rankIntroPaths(paths: RelationshipEvidence[]): ScoredIntroPath[] {
  return paths.map(scoreIntroPath).sort((a, b) => b.score - a.score);
}
