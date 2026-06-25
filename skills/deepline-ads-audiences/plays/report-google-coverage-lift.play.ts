import { definePlay } from 'deepline';

type AudienceMetric = {
  key?: string;
  label: string;
  audience_id: string;
  match_rate_pct: number;
  uploaded_rows?: number;
  source_coverage_pct?: number;
  deepline_spend_usd?: number;
  notes?: string;
};

type SpendBreakdown = {
  low_cost_hash_usd?: number;
  contact_fallback_usd?: number;
  linkedin_refresh_usd?: number;
  total_usd?: number;
};

type Input = {
  recipient_name?: string;
  account_name: string;
  account_id: string;
  segment_name: string;
  source_rows?: number;
  baseline: AudienceMetric;
  comparisons: AudienceMetric[];
  spend?: SpendBreakdown;
  recommendation_label?: string;
};

type ReportRow = {
  label: string;
  audience_id: string;
  match_rate_pct: number;
  delta_points_vs_baseline: number;
  relative_lift_vs_baseline_pct: number;
  uploaded_rows?: number;
  estimated_matched_identifiers?: number;
  incremental_matched_identifiers_vs_baseline?: number;
  deepline_spend_usd?: number;
  cost_per_incremental_matched_identifier_usd?: number;
  notes?: string;
};

function round(value: number, places = 2): number {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

function formatPct(value: number): string {
  return `${round(value, 1)}%`;
}

function formatPoints(value: number): string {
  return `${round(value, 1)} point${Math.abs(round(value, 1)) === 1 ? '' : 's'}`;
}

function formatMoney(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) return 'not specified';
  return `$${round(value, 2).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function estimatedMatched(audience: AudienceMetric): number | undefined {
  if (audience.uploaded_rows === undefined) return undefined;
  return Math.round(audience.uploaded_rows * (audience.match_rate_pct / 100));
}

function totalSpend(spend: SpendBreakdown | undefined): number | undefined {
  if (!spend) return undefined;
  if (spend.total_usd !== undefined) return spend.total_usd;
  const parts = [
    spend.low_cost_hash_usd,
    spend.contact_fallback_usd,
    spend.linkedin_refresh_usd,
  ].filter((value): value is number => value !== undefined);
  if (parts.length === 0) return undefined;
  return parts.reduce((sum, value) => sum + value, 0);
}

function buildReportRow(
  baseline: AudienceMetric,
  audience: AudienceMetric,
): ReportRow {
  const baselineMatched = estimatedMatched(baseline);
  const matched = estimatedMatched(audience);
  const incrementalMatched =
    baselineMatched !== undefined && matched !== undefined
      ? matched - baselineMatched
      : undefined;
  const deltaPoints = audience.match_rate_pct - baseline.match_rate_pct;
  const relativeLift =
    baseline.match_rate_pct > 0
      ? (deltaPoints / baseline.match_rate_pct) * 100
      : 0;
  const spend = audience.deepline_spend_usd;
  const costPerIncremental =
    spend !== undefined &&
    incrementalMatched !== undefined &&
    incrementalMatched > 0
      ? spend / incrementalMatched
      : undefined;

  return {
    label: audience.label,
    audience_id: audience.audience_id,
    match_rate_pct: audience.match_rate_pct,
    delta_points_vs_baseline: round(deltaPoints, 2),
    relative_lift_vs_baseline_pct: round(relativeLift, 2),
    uploaded_rows: audience.uploaded_rows,
    estimated_matched_identifiers: matched,
    incremental_matched_identifiers_vs_baseline: incrementalMatched,
    deepline_spend_usd: spend,
    cost_per_incremental_matched_identifier_usd:
      costPerIncremental === undefined ? undefined : round(costPerIncremental),
    notes: audience.notes,
  };
}

function bestRow(rows: ReportRow[]): ReportRow {
  return rows.reduce((best, row) =>
    row.match_rate_pct > best.match_rate_pct ? row : best,
  );
}

function spendSentence(spend: SpendBreakdown | undefined): string {
  const total = totalSpend(spend);
  if (!spend || total === undefined) {
    return 'I do not have a complete Deepline spend total attached to this report.';
  }

  const parts: string[] = [];
  if (spend.low_cost_hash_usd !== undefined) {
    parts.push(`low-cost hash pass: ${formatMoney(spend.low_cost_hash_usd)}`);
  }
  if (spend.contact_fallback_usd !== undefined) {
    parts.push(
      `expanded contact fallback: ${formatMoney(spend.contact_fallback_usd)}`,
    );
  }
  if (spend.linkedin_refresh_usd !== undefined) {
    parts.push(`LinkedIn refresh: ${formatMoney(spend.linkedin_refresh_usd)}`);
  }
  return `Deepline spend recorded for the workflow was ${formatMoney(total)}${
    parts.length ? ` (${parts.join('; ')})` : ''
  }.`;
}

function buildMessage(input: Input, rows: ReportRow[]): string {
  const baseline = input.baseline;
  const best = bestRow(rows);
  const recommendation =
    input.recommendation_label || best.label.replace(/^L\d+\s*/i, '').trim();
  const baselineMatched = estimatedMatched(baseline);
  const bestIncremental = best.incremental_matched_identifiers_vs_baseline;
  const spendTotal = totalSpend(input.spend);
  const costPerIncremental =
    spendTotal !== undefined &&
    bestIncremental !== undefined &&
    bestIncremental > 0
      ? spendTotal / bestIncremental
      : undefined;

  const lines = [
    `${input.recipient_name ?? 'Team'} - quick follow-up on the Google Ads audience coverage test for ${input.segment_name}.`,
    '',
    `We uploaded the QA audiences into ${input.account_name} (${input.account_id}). Baseline work-email hashes matched at ${formatPct(
      baseline.match_rate_pct,
    )}${baseline.uploaded_rows ? ` across ${baseline.uploaded_rows.toLocaleString()} uploaded rows` : ''}.`,
    `The best enriched audience was ${best.label} (${best.audience_id}) at ${formatPct(
      best.match_rate_pct,
    )}, a +${formatPoints(best.delta_points_vs_baseline)} lift versus baseline.`,
  ];

  if (baselineMatched !== undefined && best.estimated_matched_identifiers) {
    lines.push(
      `That is roughly ${best.estimated_matched_identifiers.toLocaleString()} matched identifiers versus about ${baselineMatched.toLocaleString()} on the baseline, or about ${(
        bestIncremental ?? 0
      ).toLocaleString()} incremental matched identifiers.`,
    );
  }

  lines.push(spendSentence(input.spend));

  if (costPerIncremental !== undefined) {
    lines.push(
      `Using the full recorded spend, the blended cost was about ${formatMoney(
        costPerIncremental,
      )} per incremental matched identifier versus the baseline.`,
    );
  }

  lines.push(
    '',
    'The important takeaway: work-email-only upload was materially underpowered. The cheap LimaData/Aviato hash pass gave the first large jump, and the LinkedIn-refresh + Lima/Aviato variant produced the strongest Google result. Source details did not improve the Google match rate in this test, so I would keep the production default hash-only unless we need those fields for QA.',
    '',
    `Recommendation: use ${recommendation} for the first campaign test and keep the work-hash-only list as the holdout/baseline comparison.`,
    '',
    'Audience readout:',
    ...rows.map(
      (row) =>
        `- ${row.label}: ${row.audience_id}, ${formatPct(
          row.match_rate_pct,
        )} match, ${row.delta_points_vs_baseline >= 0 ? '+' : ''}${formatPoints(
          row.delta_points_vs_baseline,
        )} vs baseline${
          row.uploaded_rows
            ? `, ${row.uploaded_rows.toLocaleString()} uploaded rows`
            : ''
        }`,
    ),
  );

  return lines.join('\n');
}

export default definePlay(
  'ads-audience-report-google-coverage-lift',
  async (ctx, input: Input) => {
    if (!input.comparisons.length) {
      throw new Error('At least one comparison audience is required.');
    }

    const rows = [
      buildReportRow(input.baseline, input.baseline),
      ...input.comparisons.map((audience) =>
        buildReportRow(input.baseline, audience),
      ),
    ];
    const best = bestRow(rows);
    const spendTotal = totalSpend(input.spend);
    const reportRows = await ctx
      .dataset('google_coverage_lift_report', rows)
      .run({ description: 'Google Ads audience match-rate lift report.' });

    return {
      account_name: input.account_name,
      account_id: input.account_id,
      segment_name: input.segment_name,
      source_rows: input.source_rows,
      baseline_match_rate_pct: input.baseline.match_rate_pct,
      best_audience_label: best.label,
      best_audience_id: best.audience_id,
      best_match_rate_pct: best.match_rate_pct,
      best_delta_points_vs_baseline: best.delta_points_vs_baseline,
      deepline_spend_usd: spendTotal,
      report_rows: reportRows,
      follow_up_message: buildMessage(input, rows),
    };
  },
);
