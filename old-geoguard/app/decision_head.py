# Decision Head: Detector, Policy Mapper, Arbiter orchestration

from app.schema import FeatureInput, FeatureOutput, Evidence, Metadata
from app.retrieval import retrieve_feature_clauses, retrieve_regulation_sections
from app.normalization import normalize_feature
from app.calibration import calibrate_confidence
from app.utils import get_structured_response
from app.router import router_decision
from app.storage import persist_audit
from app.llm_schemas import DetectorResponse, PolicyMapperResponse, ArbiterResponse
import datetime

def build_detector_prompt(glossary, feature_clauses):
    return f"""You are a legal compliance detector. Determine if this feature requires geo-specific LEGAL compliance (not just business geofencing).

Use the glossary and feature clauses below to make your determination.

Glossary:
{glossary}

Feature clauses (top-k):
{feature_clauses}

Analyze the feature and determine:
- detector_decision: "YES" if legal compliance is required, "NO" if it's just business logic, "REVIEW" if unclear
- reason: Brief evidence-based explanation of your decision
- feature_spans: Relevant quotes from the feature that support your decision"""

def build_policy_mapper_prompt(feature_spans, reg_sections):
    return f"""You are a policy mapper. Map this feature to specific compliance control types and applicable regulations.

Feature evidence:
{feature_spans}

Available regulation sections:
{reg_sections}

Analyze and provide:
- control_type: List of applicable control types (e.g., "age_gating", "data_retention", "content_moderation")
- regulations: List of applicable regulations (e.g., "UT-SMRA", "EU-DSA", "CA-SB976")
- reg_snippets: Exact quotes from regulations that apply to this feature
- reason: Brief explanation of why these controls and regulations apply"""

def build_arbiter_prompt(feature_id, detector_json, policymapper_json, retrieval_ids, runtime_info):
    return f"""You are the final arbiter. Make the compliance decision based on the detector and policy mapper analysis.

Detector Analysis: {detector_json}
Policy Mapper Analysis: {policymapper_json}

Make your final decision:
- feature_id: "{feature_id}"
- decision: "YES" (compliance required), "NO" (no compliance needed), or "REVIEW" (needs human review)
- confidence: Your confidence level (0.0 to 1.0)
- reasoning_summary: Clear explanation of your final decision
- evidence: Combine the most relevant feature quotes and regulation snippets
- regulations: Final list of applicable regulations
- control_type: Final list of required control types
- metadata: Use the provided retrieval and runtime information

Consider the detector's assessment and policy mapper's findings to make a well-reasoned final decision."""

def classify_feature(payload):
    # Step 1: Normalize
    feature = normalize_feature(payload)
    glossary = open("data/terminology.yaml").read()
    
    # Step 2: Router (weak supervision) - use as input signal, not final decision
    router_dec, router_conf = router_decision(feature)
    
    # Step 3: Retrieval
    feature_clauses = retrieve_feature_clauses(feature)
    reg_sections = retrieve_regulation_sections(feature)
    retrieval_ids = {"feature_clause_ids": ["f:1"], "reg_section_ids": ["dsa:IV.2.3"]}  # Placeholder
    runtime_info = {"pipeline_version": "0.1.0", "prompt_version": "0.1.0", "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    # Step 4: LLM Decision Head (Gemini) - Always use LLM for better accuracy
    print(f"Using LLM classification for {feature.get('feature_id', 'unknown')}")
    
    # Detector - Using structured response
    detector_prompt = build_detector_prompt(glossary, feature_clauses)
    detector_response = get_structured_response(detector_prompt, DetectorResponse)
    
    # Policy Mapper - Using structured response
    policymapper_prompt = build_policy_mapper_prompt(feature_clauses, reg_sections)
    policymapper_response = get_structured_response(policymapper_prompt, PolicyMapperResponse)

    # Arbiter (self-consistency n=3) - Using structured response
    arbiter_outputs = []
    confidences = []
    for i in range(3):
        print(f"   Arbiter run {i+1}/3")
        arbiter_prompt = build_arbiter_prompt(
            feature.get("feature_id", ""), 
            detector_response.model_dump(), 
            policymapper_response.model_dump(), 
            retrieval_ids, 
            runtime_info
        )
        arbiter_response = get_structured_response(arbiter_prompt, ArbiterResponse)
        
        if arbiter_response.decision in ["YES", "NO", "REVIEW"]:
            arbiter_outputs.append(arbiter_response)
            confidences.append(arbiter_response.confidence)
        else:
            print(f"   Invalid decision from arbiter response {i+1}: {arbiter_response.decision}")
            continue

    # Majority vote for decision
    decisions = [o.decision for o in arbiter_outputs]
    final_decision = max(set(decisions), key=decisions.count) if decisions else "REVIEW"
    final_confidence = calibrate_confidence(confidences) if confidences else 0.5
    
    # Use first valid output for evidence
    final_output = arbiter_outputs[0] if arbiter_outputs else None
    if not final_output:
        # Create fallback output
        from app.llm_schemas import Evidence as LLMEvidence
        final_output = ArbiterResponse(
            feature_id=feature.get("feature_id", ""),
            decision="REVIEW",
            confidence=0.5,
            reasoning_summary="Insufficient evidence or LLM parsing failed.",
            evidence=LLMEvidence(
                feature_spans=[feature.get("feature_description", "")], 
                reg_snippets=[]
            ),
            regulations=[],
            control_type=[],
            metadata={"retrieval": retrieval_ids, "runtime": runtime_info}
        )

    print(f"   Final decision: {final_decision} (confidence: {final_confidence:.3f})")

    output = FeatureOutput(
        feature_id=final_output.feature_id,
        decision=final_decision,
        confidence=final_confidence,
        reasoning_summary=final_output.reasoning_summary,
        evidence=Evidence(
            feature_spans=final_output.evidence.feature_spans,
            reg_snippets=final_output.evidence.reg_snippets
        ),
        regulations=final_output.regulations,
        control_type=final_output.control_type,
        metadata=Metadata(retrieval=retrieval_ids, runtime=runtime_info)
    )
    persist_audit(output.model_dump())
    return output.model_dump()

def batch_classify(payload):
    results = []
    for row in payload.get("rows", []):
        results.append(classify_feature(row))
    return {"results": results, "csv_path": "out/geoguard_results.csv"}
