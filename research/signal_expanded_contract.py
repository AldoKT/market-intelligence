"""Explicit product extension for an unknown lifecycle; never coerce unknown to inactive."""
from typing import Optional, Literal, List
from pydantic import model_validator
from research.signal_contract_v1 import Investigation, Persistence, InvestigationListItem, OverviewPayload, InvestigationExplorerPayload, InvestigationState
class NullablePersistence(Persistence):
    support_sessions_in_last_5: Optional[int] = None
    hard_hits_in_last_5: Optional[int] = None
    hard_hits_total_in_episode: Optional[int] = None
    support_sessions_total_in_episode: Optional[int] = None
    unsupported_streak: Optional[int] = None
    persistence_score: Optional[float] = None
class ExpandedInvestigation(Investigation):
    state: InvestigationState | Literal['UNKNOWN']
    active: Optional[bool] = None
    age_sessions: Optional[int] = None
    persistence: NullablePersistence
    @model_validator(mode='after')
    def preserve_unknown(self):
        if self.state == 'UNKNOWN':
            if self.active is not None or self.age_sessions is not None or any(v is not None for v in self.persistence.model_dump().values()):
                raise ValueError('Unknown lifecycle cannot have inferred activity or persistence')
        elif self.active is None:
            raise ValueError('Known lifecycle requires activity status')
        return self
class ExpandedListItem(InvestigationListItem):
    active: Optional[bool] = None
    persistence_hits: Optional[int] = None
    @model_validator(mode='after')
    def preserve_unknown(self):
        if self.state == 'UNKNOWN' and (self.active is not None or self.persistence_hits is not None):
            raise ValueError('Unknown lifecycle cannot be classified inactive or zero persistence')
        return self
class ExpandedOverview(OverviewPayload):
    spotlight: Optional[ExpandedListItem] = None
    active_investigations: List[ExpandedListItem]
class ExpandedExplorer(InvestigationExplorerPayload):
    items: List[ExpandedListItem]
