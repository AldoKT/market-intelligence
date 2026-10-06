"""Pilot-only extension: unknown history remains nullable and quality-labelled."""
from typing import Optional,List,Dict,Any
from pydantic import Field
from research.signal_contract_v1 import StrictModel,ActivityPoint,MarketActivityPayload

class PilotQuality(StrictModel):
    evaluation_status: str
    lifecycle_interpretation: str
    reasons: List[str] = Field(default_factory=list)
    missing_baseline_counts: Dict[str,int] = Field(default_factory=dict)
    source_scope: str = 'PILOT_UNIVERSE_ONLY'
    broker_completeness: str = 'RECONCILED_RESEARCH_CANDIDATE'

class PilotActivityPoint(ActivityPoint):
    spot_hit: Optional[bool] = None
    lifecycle_state: Optional[str] = None
    supporting_session: Optional[bool] = None
    persistence_score: Optional[float] = None
    evidence_confidence: Optional[float] = None
    diagnostic_evidence_score: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    quality: PilotQuality

class PilotActivityPayload(MarketActivityPayload):
    series: List[PilotActivityPoint]
    quality: Dict[str,Any]
