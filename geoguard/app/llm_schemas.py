# Pydantic schemas for LLM structured responses

from pydantic import BaseModel
from typing import List, Dict, Any

class DetectorResponse(BaseModel):
    detector_decision: str  # "YES", "NO", or "REVIEW"
    reason: str
    feature_spans: List[str]

class PolicyMapperResponse(BaseModel):
    control_type: List[str]
    regulations: List[str]
    reg_snippets: List[str]
    reason: str

class Evidence(BaseModel):
    feature_spans: List[str]
    reg_snippets: List[str]

class ArbiterResponse(BaseModel):
    feature_id: str
    decision: str  # "YES", "NO", or "REVIEW"
    confidence: float
    reasoning_summary: str
    evidence: Evidence
    regulations: List[str]
    control_type: List[str]
    metadata: Dict[str, Any]
