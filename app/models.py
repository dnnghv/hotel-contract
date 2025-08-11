from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    Pricing = "Pricing"
    Season = "Season"
    Blackout = "Blackout"
    Allotment = "Allotment"
    Cutoff = "Cutoff"
    Cancellation = "Cancellation"
    NoShow = "NoShow"
    Surcharge = "Surcharge"
    Tax = "Tax"
    StopSell = "StopSell"
    Promotion = "Promotion"
    Payment = "Payment"
    Other = "Other"


class SourceAnchor(BaseModel):
    page: Optional[int] = None
    heading: Optional[str] = None
    table_id: Optional[str] = None


class SeasonWindow(BaseModel):
    from_: date = Field(alias="from")
    to: date


class RateRow(BaseModel):
    date_from: date
    date_to: date
    rate: float
    currency: str
    notes: Optional[str] = None


class Clause(BaseModel):
    id: str
    type: ClauseType
    title: str
    scope: Optional[Dict[str, Any]] = None
    season: Optional[List[SeasonWindow]] = None
    blackout: Optional[List[str]] = None
    table: Optional[List[RateRow]] = None
    policy: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    source_anchor: Optional[SourceAnchor] = None
    confidence: float


class ContractMeta(BaseModel):
    hotel: str
    sign_date: date
    currency: str
    source_file: str


class BaseContract(BaseModel):
    contract_id: str
    meta: ContractMeta
    clauses: List[Clause]


class ChangeOp(str, Enum):
    add = "add"
    replace = "replace"
    remove = "remove"


class ChangeType(str, Enum):
    RateAdjustment = "RateAdjustment"
    Promotion = "Promotion"
    AllotmentUpdate = "AllotmentUpdate"
    StopSell = "StopSell"
    OpenSell = "OpenSell"
    PolicyUpdate = "PolicyUpdate"
    TaxUpdate = "TaxUpdate"
    SurchargeUpdate = "SurchargeUpdate"


class ChangeTarget(BaseModel):
    clause_id: Optional[str] = None
    type: Optional[str] = None
    scope: Optional[Dict[str, Any]] = None


class Change(BaseModel):
    id: str
    op: ChangeOp
    type: ChangeType
    target: ChangeTarget
    payload: Optional[Dict[str, Any]] = None
    effective_from: date
    effective_to: Optional[date] = None
    notes: Optional[str] = None
    confidence: float


class ChangeSet(BaseModel):
    source_doc: str
    issued_date: date
    changes: List[Change]


class Segment(BaseModel):
    page_range: List[int]
    heading: Optional[str]
    raw_md: str
    table_blocks: List[str] = Field(default_factory=list)


class Chunk(BaseModel):
    label: Optional[str] = None
    markdown: str
    page_range: List[int] = Field(default_factory=list)
    source_heading: Optional[str] = None 