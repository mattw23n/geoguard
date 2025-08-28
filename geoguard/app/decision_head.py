# Decision Head: Detector, Policy Mapper, Arbiter orchestration

from app.schema import FeatureInput, FeatureOutput, Evidence, Metadata
from app.retrieval import retrieve_feature_clauses, retrieve_regulation_sections
from app.normalization import normalize_feature
from app.calibration import calibrate_confidence
from app.utils import get_gemini_response
from app.router import router_decision
from app.storage import persist_audit
import datetime
import json
import re

def clean_and_parse_json(text):
    """Clean and parse JSON response from LLM"""
    try:
        # Remove any markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON object in the text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)
        else:
            # If no JSON found, try parsing the whole text
            return json.loads(text.strip())
    except Exception as e:
        print(f"   ⚠️ JSON parsing failed: {e}")
        print(f"   Raw text: {text[:200]}...")
        return None

def build_detector_prompt(glossary, feature_clauses):
    return f"""You are a legal compliance detector. Analyze if this feature requires geo-specific LEGAL compliance (not just business geofencing).

Use the glossary and feature clauses below to make your determination.

Glossary:
{glossary}

Feature clauses (top-k):
{feature_clauses}

RESPOND WITH ONLY VALID JSON IN THIS EXACT FORMAT:
{{
    "detector_decision": "YES",
    "reason": "Brief evidence-based reason here",
    "feature_spans": ["relevant quote from feature"]
}}

Use "YES" if legal compliance is required, "NO" if it's just business logic."""

def build_policy_mapper_prompt(feature_spans, reg_sections):
    return f"""You are a policy mapper. Map the feature to specific compliance control types and regulations.

Feature evidence:
{feature_spans}

Regulation sections (top-k):
{reg_sections}

RESPOND WITH ONLY VALID JSON IN THIS EXACT FORMAT:
{{
    "control_type": ["age_gating", "data_retention"],
    "regulations": ["UT-SMRA", "EU-DSA"],
    "reg_snippets": ["exact quotes from regulations"],
    "reason": "Brief mapping explanation"
}}"""

def build_arbiter_prompt(feature_id, detector_json, policymapper_json, retrieval_ids, runtime_info):
    return f"""You are the final arbiter. Make the compliance decision based on detector and policy mapper outputs.

Detector Output: {detector_json}
Policy Mapper Output: {policymapper_json}

RESPOND WITH ONLY VALID JSON IN THIS EXACT FORMAT:
{{
    "feature_id": "{feature_id}",
    "decision": "YES",
    "confidence": 0.85,
    "reasoning_summary": "Brief explanation of decision",
    "evidence": {{
        "feature_spans": ["relevant feature quotes"],
        "reg_snippets": ["relevant regulation quotes"]
    }},
    "regulations": ["applicable regulations"],
    "control_type": ["applicable control types"],
    "metadata": {{
        "retrieval": {retrieval_ids},
        "runtime": {runtime_info}
    }}
}}

Use "YES" for compliance required, "NO" for no compliance needed, "REVIEW" for unclear cases."""

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
    print(f"🤖 Using LLM classification for {feature.get('feature_id', 'unknown')}")
    
    # Detector
    detector_prompt = build_detector_prompt(glossary, feature_clauses)
    detector_result = get_gemini_response(detector_prompt)
    detector_json_raw = detector_result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
    
    detector_json = clean_and_parse_json(detector_json_raw)
    if not detector_json:
        detector_json = {"detector_decision": "REVIEW", "reason": "Failed to parse detector response", "feature_spans": []}

    # Policy Mapper
    policymapper_prompt = build_policy_mapper_prompt(feature_clauses, reg_sections)
    policymapper_result = get_gemini_response(policymapper_prompt)
    policymapper_json_raw = policymapper_result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
    
    policymapper_json = clean_and_parse_json(policymapper_json_raw)
    if not policymapper_json:
        policymapper_json = {"control_type": [], "regulations": [], "reg_snippets": [], "reason": "Failed to parse policy mapper response"}

    # Arbiter (self-consistency n=3)
    arbiter_outputs = []
    confidences = []
    for i in range(3):
        print(f"   🔄 Arbiter run {i+1}/3")
        arbiter_prompt = build_arbiter_prompt(
            feature.get("feature_id", ""), detector_json, policymapper_json, retrieval_ids, runtime_info)
        arbiter_result = get_gemini_response(arbiter_prompt)
        arbiter_json_raw = arbiter_result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        
        arbiter_json = clean_and_parse_json(arbiter_json_raw)
        if arbiter_json and arbiter_json.get("decision"):
            arbiter_outputs.append(arbiter_json)
            confidences.append(arbiter_json.get("confidence", 0.5))
        else:
            print(f"   ❌ Failed to parse arbiter response {i+1}")
            continue

    # Majority vote for decision
    decisions = [o.get("decision", "REVIEW") for o in arbiter_outputs]
    final_decision = max(set(decisions), key=decisions.count) if decisions else "REVIEW"
    final_confidence = calibrate_confidence(confidences) if confidences else 0.5
    
    # Use first valid output for evidence
    final_output = next((o for o in arbiter_outputs if o.get("decision", None)), None)
    if not final_output:
        final_output = {
            "feature_id": feature.get("feature_id", ""),
            "decision": "REVIEW",
            "confidence": 0.5,
            "reasoning_summary": "Insufficient evidence or LLM parsing failed.",
            "evidence": {"feature_spans": [feature.get("feature_description", "")], "reg_snippets": []},
            "regulations": [],
            "control_type": [],
            "metadata": {"retrieval": retrieval_ids, "runtime": runtime_info}
        }

    print(f"   ✅ Final decision: {final_decision} (confidence: {final_confidence:.3f})")

    output = FeatureOutput(
        feature_id=final_output["feature_id"],
        decision=final_decision,
        confidence=final_confidence,
        reasoning_summary=final_output.get("reasoning_summary", ""),
        evidence=Evidence(
            feature_spans=final_output.get("evidence", {}).get("feature_spans", []),
            reg_snippets=final_output.get("evidence", {}).get("reg_snippets", [])
        ),
        regulations=final_output.get("regulations", []),
        control_type=final_output.get("control_type", []),
        metadata=Metadata(retrieval=retrieval_ids, runtime=runtime_info)
    )
    persist_audit(output.model_dump())
    return output.model_dump()

def batch_classify(payload):
    results = []
    for row in payload.get("rows", []):
        results.append(classify_feature(row))
    return {"results": results, "csv_path": "out/geoguard_results.csv"}
