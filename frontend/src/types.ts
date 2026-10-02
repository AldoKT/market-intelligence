export type InvestigationState =
  | "NO_INVESTIGATION"
  | "INELIGIBLE_PRICE_REGIME"
  | "EMERGING"
  | "DEVELOPING"
  | "ESTABLISHED"
  | "WEAKENING"
  | "CLOSED";

export type ContextScope =
  | "NO_ACTIVITY_CONTEXT"
  | "STOCK_SPECIFIC_ACTIVITY"
  | "PEER_CLUSTERED_ACTIVITY"
  | "MARKET_WIDE_ACTIVITY"
  | "MIXED_CONTEXT"
  | "INELIGIBLE"
  | "NO_CONTEXT";

export interface InvestigationListItem {
  symbol: string;
  peer_group: string | null;
  state: InvestigationState | string;
  active: boolean;
  evidence_confidence: number | null;
  context_scope: ContextScope | string | null;
  context_specificity_score: number | null;
  relative_turnover: number | null;
  current_5d_range_pct: number | null;
  persistence_hits: number;
  persistence_window: number;
  opened_at: string | null;
  last_updated: string;
}

export interface OverviewPayload {
  methodology_version: string;
  as_of: string;
  headline: string;
  kpis: {
    active_investigations: number;
    established: number;
    developing: number;
    emerging: number;
    weakening: number;
  };
  spotlight: InvestigationListItem | null;
  active_investigations: InvestigationListItem[];
  recent_changes: Array<{
    symbol: string;
    state: string;
    investigation_id: string | null;
    date: string;
  }>;
}

export interface InvestigationExplorerPayload {
  methodology_version: string;
  as_of: string;
  items: InvestigationListItem[];
  filters: {
    state: string[];
    peer_group: string[];
    context_scope: string[];
  };
  count?: number;
}

export interface ManifestPayload {
  methodology_version: string;
  as_of: string;
  symbols: string[];
  files: Record<string, string>;
  raw_market_activity_enrichment: boolean;
}

export interface EvidenceItem {
  evidence_id: string;
  direction: "SUPPORTING" | "CONTRADICTING" | "NEUTRAL";
  label: string;
  metric: string;
  value: number | null;
  baseline: number | null;
  relative: number | null;
  score: number | null;
  note: string;
}

export interface LookAheadCondition {
  condition_id: string;
  label: string;
  current_status: "MET" | "NOT_MET" | "NOT_APPLICABLE";
  note: string;
}

export interface InvestigationDetail {
  methodology_version: string;
  as_of: string;
  investigation_id: string | null;
  identity: {
    symbol: string;
    company_name: string | null;
    peer_group: string | null;
  };
  hypothesis: string;
  state: string;
  active: boolean;
  opened_at: string | null;
  age_sessions: number;
  gates: {
    compression_pass: boolean;
    activity_pass: boolean;
    core_activity_pass: boolean;
    spot_hit: boolean;
  };
  confidence: {
    evidence_confidence: number | null;
    diagnostic_evidence_score: number | null;
    interpretation: string;
  };
  persistence: {
    support_sessions_in_last_5: number;
    hard_hits_in_last_5: number;
    hard_hits_total_in_episode: number;
    support_sessions_total_in_episode: number;
    unsupported_streak: number;
    persistence_score: number;
  };
  metrics: {
    close: number | null;
    compression_score: number | null;
    current_5d_range_pct: number | null;
    baseline_5d_range_pct: number | null;
    compression_ratio: number | null;
    activity_score: number | null;
    relative_turnover: number | null;
    relative_volume: number | null;
    relative_transaction_count: number | null;
    relative_avg_trade_value: number | null;
    relative_top5_net_buy_share: number | null;
    foreign_net_to_turnover: number | null;
  };
  context: {
    scope: string;
    specificity_score: number | null;
    market_activity_breadth: number | null;
    market_activity_percentile: number | null;
    peer_activity_breadth: number | null;
    peer_activity_percentile: number | null;
    peer_count: number;
    peer_context_quality: string | null;
    interpretation: string;
  };
  supporting_evidence: EvidenceItem[];
  contradicting_evidence: EvidenceItem[];
  narrative_5w1h: {
    what: string;
    why: string;
    when: string;
    where: string;
    who: string;
    how: string;
  };
  look_ahead: LookAheadCondition[];
  guardrails: string[];
}

export interface SummaryPayload {
  methodology_version: string;
  as_of: string;
  investigation: InvestigationDetail;
}

export interface ActivityPoint {
  date: string;
  close: number | null;
  volume: number | null;
  transaction_count: number | null;
  turnover_idr: number | null;
  avg_trade_value_idr: number | null;
  relative_volume: number | null;
  relative_transaction_count: number | null;
  relative_turnover: number | null;
  relative_avg_trade_value: number | null;
  compression_score: number | null;
  activity_score: number | null;
  spot_hit: boolean;
  lifecycle_state: string;
}

export interface ActivityPayload {
  methodology_version: string;
  as_of: string;
  identity: InvestigationDetail["identity"];
  data_availability: {
    actual_volume: boolean;
    actual_transaction_count: boolean;
    actual_turnover: boolean;
    actual_avg_trade_value: boolean;
    relative_metrics: boolean;
  };
  current: InvestigationDetail["metrics"];
  series: ActivityPoint[];
  guardrail: string;
}

export interface ContextPayload {
  methodology_version: string;
  as_of: string;
  identity: InvestigationDetail["identity"];
  current: InvestigationDetail["context"];
  daily_market: {
    market_eligible_count?: number;
    market_activity_median?: number;
    market_activity_p75?: number;
    market_activity_gate_count?: number;
    market_activity_breadth?: number;
    market_spot_hit_count?: number;
    market_spot_hit_breadth?: number;
    date?: string;
    [key: string]: unknown;
  };
  notes: string[];
}

export interface HistoryEvent {
  date: string;
  event_type:
    | "SPOT_HIT"
    | "STATE_CHANGE"
    | "INVESTIGATION_OPENED"
    | "INVESTIGATION_CLOSED";
  state: string;
  investigation_id: string | null;
  note: string;
}

export interface EpisodeSummary {
  investigation_id: string;
  opened_at: string;
  last_linked_at: string;
  closed: boolean;
  closed_at: string | null;
  close_reason: string | null;
  active_sessions: number;
  hard_hits: number;
  support_sessions: number;
  peak_state: string;
  open_context_scope: string | null;
  max_evidence_confidence: number | null;
}

export interface HistoryPayload {
  methodology_version: string;
  as_of: string;
  identity: InvestigationDetail["identity"];
  events: HistoryEvent[];
  episodes: EpisodeSummary[];
}

export interface MethodologyPayload {
  candidate_name: string;
  status: string;
  basis: {
    eligible_observations: number;
    eligible_symbols: number;
    period: string;
    spot_hits: number;
    baseline_investigation_episodes: number;
    sensitivity_grid_combinations: number;
    peak_state_sensitive_episodes_reviewed: number;
  };
  spot_gate: {
    status: string;
    compression_score_min: number;
    activity_score_min: number;
    core_relative_min: number;
    minimum_core_metrics: number;
  };
  persistence_and_lifecycle: {
    support_compression_min: number;
    support_condition: string;
    close_after_consecutive_unsupported_sessions: number;
    established_support_sessions_in_last_5_min: number;
    established_hard_hits_in_episode_min: number;
    decision: string;
  };
  context_specificity: {
    applicability_guard: string;
    role: string;
  };
  review_findings: Record<string, string>;
  important_limitations: string[];
}

export interface ReactionValidationHorizon {
  horizon_sessions: number;
  event_n: number;
  positive_close_rate: number;
  control_positive_close_rate: number;
  reached_plus_2_rate: number;
  control_reached_plus_2_rate: number;
  breakout_5d_close_rate: number;
  control_breakout_5d_close_rate: number;
  mean_end_return: number;
  control_mean_end_return: number;
  mfe_close: number;
  control_mfe_close: number;
  mae_close: number;
  control_mae_close: number;
}

export interface ReactionValidationPayload {
  version: string;
  validation_as_of: string;
  sample_period: {
    start: string;
    end: string;
  };
  scope: string;
  status: string;
  short_horizon_robustness: string;
  primary_event: string;
  event_definition: string;
  control_definition: string;
  interpretation: string;
  guardrail: string;
  horizons: ReactionValidationHorizon[];
  significant_positive_findings: Array<{
    horizon_sessions: number;
    metric: string;
    matched_difference: number;
    cluster_bootstrap_95_ci_low: number;
    cluster_bootstrap_95_ci_high: number;
  }>;
}

