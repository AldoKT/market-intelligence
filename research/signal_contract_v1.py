
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


InvestigationState = Literal[
    "NO_INVESTIGATION",
    "INELIGIBLE_PRICE_REGIME",
    "EMERGING",
    "DEVELOPING",
    "ESTABLISHED",
    "WEAKENING",
    "CLOSED",
]

ContextScope = Literal[
    "NO_ACTIVITY_CONTEXT",
    "STOCK_SPECIFIC_ACTIVITY",
    "PEER_CLUSTERED_ACTIVITY",
    "MARKET_WIDE_ACTIVITY",
    "MIXED_CONTEXT",
    "INELIGIBLE",
    "NO_CONTEXT",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Identity(StrictModel):
    symbol: str
    company_name: Optional[str] = None
    peer_group: Optional[str] = None


class GateStatus(StrictModel):
    compression_pass: bool
    activity_pass: bool
    core_activity_pass: bool
    spot_hit: bool


class EvidenceItem(StrictModel):
    evidence_id: str
    direction: Literal["SUPPORTING", "CONTRADICTING", "NEUTRAL"]
    label: str
    metric: str
    value: Optional[float] = None
    baseline: Optional[float] = None
    relative: Optional[float] = None
    score: Optional[float] = None
    note: str


class Confidence(StrictModel):
    evidence_confidence: Optional[float] = Field(default=None, ge=0, le=100)
    diagnostic_evidence_score: Optional[float] = Field(default=None, ge=0, le=100)
    interpretation: str


class Persistence(StrictModel):
    support_sessions_in_last_5: int
    hard_hits_in_last_5: int
    hard_hits_total_in_episode: int
    support_sessions_total_in_episode: int
    unsupported_streak: int
    persistence_score: float = Field(ge=0, le=100)


class ContextSnapshot(StrictModel):
    scope: ContextScope
    specificity_score: Optional[float] = Field(default=None, ge=0, le=100)
    market_activity_breadth: Optional[float] = Field(default=None, ge=0, le=1)
    market_activity_percentile: Optional[float] = Field(default=None, ge=0, le=1)
    peer_activity_breadth: Optional[float] = Field(default=None, ge=0, le=1)
    peer_activity_percentile: Optional[float] = Field(default=None, ge=0, le=1)
    peer_count: int
    peer_context_quality: Optional[str] = None
    interpretation: str


class MarketMetrics(StrictModel):
    close: Optional[float] = None
    compression_score: Optional[float] = None
    current_5d_range_pct: Optional[float] = None
    baseline_5d_range_pct: Optional[float] = None
    compression_ratio: Optional[float] = None
    activity_score: Optional[float] = None
    relative_turnover: Optional[float] = None
    relative_volume: Optional[float] = None
    relative_transaction_count: Optional[float] = None
    relative_avg_trade_value: Optional[float] = None
    relative_top5_net_buy_share: Optional[float] = None
    foreign_net_to_turnover: Optional[float] = None


class Narrative5W1H(StrictModel):
    what: str
    why: str
    when: str
    where: str
    who: str
    how: str


class LookAheadCondition(StrictModel):
    condition_id: str
    label: str
    current_status: Literal["MET", "NOT_MET", "NOT_APPLICABLE"]
    note: str


class Investigation(StrictModel):
    methodology_version: str
    as_of: str
    investigation_id: Optional[str] = None
    identity: Identity
    hypothesis: str
    state: InvestigationState
    active: bool
    opened_at: Optional[str] = None
    age_sessions: int = 0
    gates: GateStatus
    confidence: Confidence
    persistence: Persistence
    metrics: MarketMetrics
    context: ContextSnapshot
    supporting_evidence: List[EvidenceItem]
    contradicting_evidence: List[EvidenceItem]
    narrative_5w1h: Narrative5W1H
    look_ahead: List[LookAheadCondition]
    guardrails: List[str]


class ActivityPoint(StrictModel):
    date: str
    close: Optional[float] = None
    volume: Optional[float] = None
    transaction_count: Optional[float] = None
    turnover_idr: Optional[float] = None
    avg_trade_value_idr: Optional[float] = None
    relative_volume: Optional[float] = None
    relative_transaction_count: Optional[float] = None
    relative_turnover: Optional[float] = None
    relative_avg_trade_value: Optional[float] = None
    compression_score: Optional[float] = None
    activity_score: Optional[float] = None
    spot_hit: bool = False
    lifecycle_state: str


class MarketActivityPayload(StrictModel):
    methodology_version: str
    as_of: str
    identity: Identity
    data_availability: Dict[str, bool]
    current: MarketMetrics
    series: List[ActivityPoint]
    guardrail: str


class ContextPayload(StrictModel):
    # Optional enrichment stays separate from the historical current snapshot.
    company_snapshot: Optional[Dict[str, Any]] = None
    fundamental_peers: Optional[List[Dict[str, Any]]] = None
    market_history: Optional[List[Dict[str, Any]]] = None
    context_period: Optional[Dict[str, str]] = None
    news_archive: Optional[Dict[str, Any]] = None
    relevant_news: Optional[List[Dict[str, Any]]] = None
    corporate_events: Optional[List[Dict[str, str]]] = None
    source_availability: Optional[Dict[str, bool]] = None
    methodology_version: str
    as_of: str
    identity: Identity
    current: ContextSnapshot
    daily_market: Dict[str, Any]
    notes: List[str]


class HistoryEvent(StrictModel):
    date: str
    event_type: Literal[
        "SPOT_HIT",
        "STATE_CHANGE",
        "INVESTIGATION_OPENED",
        "INVESTIGATION_CLOSED",
    ]
    state: str
    investigation_id: Optional[str] = None
    note: str


class EpisodeSummary(StrictModel):
    investigation_id: str
    opened_at: str
    last_linked_at: str
    closed: bool
    closed_at: Optional[str] = None
    close_reason: Optional[str] = None
    active_sessions: int
    hard_hits: int
    support_sessions: int
    peak_state: str
    open_context_scope: Optional[str] = None
    max_evidence_confidence: Optional[float] = None


class HistoryPayload(StrictModel):
    methodology_version: str
    as_of: str
    identity: Identity
    events: List[HistoryEvent]
    episodes: List[EpisodeSummary]


class InvestigationListItem(StrictModel):
    symbol: str
    peer_group: Optional[str] = None
    state: str
    active: bool
    evidence_confidence: Optional[float] = None
    context_scope: Optional[str] = None
    context_specificity_score: Optional[float] = None
    relative_turnover: Optional[float] = None
    current_5d_range_pct: Optional[float] = None
    persistence_hits: int
    persistence_window: int = 5
    opened_at: Optional[str] = None
    last_updated: str


class OverviewPayload(StrictModel):
    methodology_version: str
    as_of: str
    headline: str
    kpis: Dict[str, int]
    spotlight: Optional[InvestigationListItem] = None
    active_investigations: List[InvestigationListItem]
    recent_changes: List[Dict[str, Any]]


class InvestigationExplorerPayload(StrictModel):
    methodology_version: str
    as_of: str
    items: List[InvestigationListItem]
    filters: Dict[str, List[str]]
