export type InvestigationState =
  | "UNKNOWN"
  | "UNKNOWN"
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
  company_name?: string | null;
  peer_group: string | null;
  pattern_type?: string | null;
  state: InvestigationState | string;
  active: boolean | null;
  evidence_confidence: number | null;
  context_scope: ContextScope | string | null;
  context_specificity_score: number | null;
  close?: number | null;
  daily_change_pct?: number | null;
  relative_turnover: number | null;
  current_5d_range_pct: number | null;
  persistence_hits: number | null;
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
    established?: number;
    developing?: number;
    emerging?: number;
    weakening?: number;
    pilot_symbols?: number;
    observed_episodes?: number;
    withheld_analysis_sessions?: number;
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
  active: boolean | null;
  opened_at: string | null;
  age_sessions: number | null;
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
    support_sessions_in_last_5: number | null;
    hard_hits_in_last_5: number | null;
    hard_hits_total_in_episode: number | null;
    support_sessions_total_in_episode: number | null;
    unsupported_streak: number | null;
    persistence_score: number | null;
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
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close: number | null;
  volume: number | null;
  transaction_count: number | null;
  turnover_idr: number | null;
  avg_trade_value_idr: number | null;
  market_cap?: number | null;
  net_foreign_inflow?: number | null;
  foreign_share?: number | null;
  volume_baseline_20d?: number | null;
  transaction_count_baseline_20d?: number | null;
  turnover_baseline_20d?: number | null;
  avg_trade_value_baseline_20d?: number | null;
  relative_volume: number | null;
  relative_transaction_count: number | null;
  relative_turnover: number | null;
  relative_avg_trade_value: number | null;
  compression_score: number | null;
  activity_score: number | null;
  evidence_confidence?: number | null;
  diagnostic_evidence_score?: number | null;
  persistence_score?: number | null;
  supporting_session?: boolean | null;
  spot_hit: boolean | null;
  lifecycle_state: string | null;
  quality?: { evaluation_status: string; lifecycle_interpretation: string; reasons: string[]; missing_baseline_counts: Record<string, number> };
}

export interface ActivityPayload {
  quality?: { analysis_sessions: number; evaluated_sessions: number; withheld_sessions: number; missing_dates: string[]; broker_scope_mismatch_dates: string[]; broker_completeness_attested: boolean; context_scope: string };
  methodology_version: string;
  as_of: string;
  identity: InvestigationDetail["identity"];
  data_availability: {
    actual_volume: boolean;
    actual_transaction_count: boolean;
    actual_turnover: boolean;
    actual_avg_trade_value: boolean;
    actual_ohlc?: boolean;
    relative_metrics: boolean;
  };
  current: InvestigationDetail["metrics"];
  series: ActivityPoint[];
  guardrail: string;
  source_note?: string;
}

export interface ContextPayload {
  methodology_version: string;
  as_of: string;
  identity: InvestigationDetail["identity"];
  current: InvestigationDetail["context"];
  peer_comparison?: Array<{
    symbol: string;
    activity_score: number | null;
    relative_turnover: number | null;
    context_scope: string | null;
    context_specificity_score: number | null;
    state: string;
  }>;
  source_availability?: {
    sector_market_series?: boolean;
    company_fundamentals?: boolean;
    corporate_events?: boolean;
    news?: boolean;
    peer_comparison?: boolean;
    market_context?: boolean;
  };
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
  relevant_news?: Array<{
    title: string | null;
    timestamp: string;
    source?: string | null;
    thumbnail?: string | null;
    tags?: string[];
  }>;
  corporate_events?: Array<{ date: string; type: string; detail: string }>;
  company_fundamentals?: { available: boolean; metrics: Array<{label:string;value:string}> };
  sector_context?: { available: boolean; series: unknown[]; note?: string };
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

export interface PilotMethodologyPayload {
  methodology_version: string; as_of: string;
  detector: { analysis_start:string; analysis_end:string; baseline_requires_preceding_sessions:number; metric_baseline_sessions:number;
    thresholds:{compression:number;activity:number;core_relative:number;core_count:number};
    by_symbol:Record<string,{analysis_sessions:number;evaluated:number;not_evaluated:number;spot_hits:number}> };
  lifecycle: {thresholds:{established_support_count:number;persistence_window:number;established_hard_hits:number;close_after_unsupported:number}};
  gate_d:{approved:boolean};
}
export type MethodologyPayload = LegacyMethodologyPayload | PilotMethodologyPayload;
export interface LegacyMethodologyPayload {
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

