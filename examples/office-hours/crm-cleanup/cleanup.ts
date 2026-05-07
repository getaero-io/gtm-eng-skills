export type CrmRow = {
  id: string;
  companyName?: string;
  domain?: string;
  contactEmail?: string;
  ownerEmail?: string;
  lifecycleStage?: string;
};

export type CleanupDecision =
  | { action: "write"; id: string; normalized: Required<CrmRow>; reasons: string[] }
  | { action: "review"; id: string; reasons: string[] };

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const DOMAIN_RE = /^(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+$/i;

function normalizeDomain(domain: string | undefined): string {
  return String(domain || "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0] || "";
}

export function decideCleanup(row: CrmRow): CleanupDecision {
  const reasons: string[] = [];
  const domain = normalizeDomain(row.domain);
  const contactEmail = String(row.contactEmail || "").trim().toLowerCase();
  const ownerEmail = String(row.ownerEmail || "").trim().toLowerCase();
  const companyName = String(row.companyName || "").trim();
  const lifecycleStage = String(row.lifecycleStage || "lead").trim().toLowerCase();

  if (!companyName) reasons.push("missing_company_name");
  if (!DOMAIN_RE.test(domain)) reasons.push("invalid_domain");
  if (!EMAIL_RE.test(contactEmail)) reasons.push("invalid_contact_email");
  if (!EMAIL_RE.test(ownerEmail)) reasons.push("invalid_owner_email");

  if (reasons.length > 0) {
    return { action: "review", id: row.id, reasons };
  }

  return {
    action: "write",
    id: row.id,
    reasons: ["passed_deterministic_checks"],
    normalized: {
      id: row.id,
      companyName,
      domain,
      contactEmail,
      ownerEmail,
      lifecycleStage,
    },
  };
}

export function summarizeCleanup(rows: CrmRow[]) {
  const decisions = rows.map(decideCleanup);
  return {
    writeCount: decisions.filter((decision) => decision.action === "write").length,
    reviewCount: decisions.filter((decision) => decision.action === "review").length,
    decisions,
  };
}
