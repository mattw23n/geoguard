# Pydantic models for input/output schema
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class FeatureInput(BaseModel):
    feature_id: str
    feature_name: str
    feature_description: str
    prd: Optional[str] = ""
    trd: Optional[str] = ""

class Evidence(BaseModel):
    feature_spans: List[str]
    reg_snippets: List[str]

class Metadata(BaseModel):
    retrieval: Dict[str, List[str]]
    runtime: Dict[str, str]

class FeatureOutput(BaseModel):
    feature_id: str
    decision: str
    confidence: float
    reasoning_summary: str
    evidence: Evidence
    regulations: List[str]
    control_type: List[str]
    metadata: Metadata
