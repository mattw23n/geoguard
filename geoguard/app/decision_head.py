# Decision Head: Detector, Policy Mapper, Arbiter orchestration

from app.schema import FeatureInput, FeatureOutput, Evidence, Metadata
from app.retrieval import retrieve_feature_clauses, retrieve_regulation_sections
from app.normalization import normalize_feature
from app.calibration import calibrate_confidence
from app.utils import get_gemini_response
from app.router import router_decision
from app.storage import persist_audit
import datetime

def build_detector_prompt(glossary, feature_clauses):
    return f"""SYSTEM: You determine if a feature implies geo-specific LEGAL compliance logic (not business geofencing).\nUse the glossary and retrieved feature clauses. Output YES or NO with a short evidence-based reason.\nUSER:\nGlossary:\n{glossary}\nFeature clauses (top-k):\n{feature_clauses}\nReturn JSON:\n{{\"detector_decision\":\"YES|NO\",\"reason\":\"1-2 sentences (cite a short feature quote)\",\"feature_spans\":["..."] }}"""

def build_policy_mapper_prompt(feature_spans, reg_sections):
    return f"""SYSTEM: Map the feature to compliance control types and likely regulations.\nUse ONLY the retrieved regulation sections. Quote exact snippets.\nUSER:\nFeature evidence:\n{feature_spans}\nRegulation sections (top-k):\n{reg_sections}\nReturn JSON:\n{{\"control_type\":["..."],\"regulations\":["..."],\"reg_snippets\":["exact quotes with section ids"],\"reason\":\"1-2 sentences\"}}"""

def build_arbiter_prompt(feature_id, detector_json, policymapper_json, retrieval_ids, runtime_info):
    return f"""SYSTEM: Produce the final decision with confidence.\nConsider Detector + Policy Mapper outputs. If evidence is weak or conflicting, set decision=REVIEW.\nUSER:\nDetector: {detector_json}\nPolicyMapper: {policymapper_json}\nReturn JSON:\n{{\n \"feature_id\": \"{feature_id}\",\n \"decision\": \"YES|NO|REVIEW\",\n \"confidence\": 0.0-1.0,\n \"reasoning_summary\": \"1-3 sentences; reference quoted evidence\",\n \"evidence\": {{ \"feature_spans\": [...], \"reg_snippets\": [...] }},\n \"regulations\": [...],\n \"control_type\": [...],\n \"metadata\": {{ \"retrieval\": {retrieval_ids}, \"runtime\": {runtime_info} }}\n}}"""

def classify_feature(payload):
    # Step 1: Normalize
    feature = normalize_feature(payload)
    glossary = open("data/terminology.yaml").read()
    # Step 2: Router (weak supervision)
    router_dec, router_conf = router_decision(feature)
    # Step 3: Retrieval
    feature_clauses = retrieve_feature_clauses(feature)
    reg_sections = retrieve_regulation_sections(feature)
    retrieval_ids = {"feature_clause_ids": ["f:1"], "reg_section_ids": ["dsa:IV.2.3"]}  # Placeholder
    runtime_info = {"pipeline_version": "0.1.0", "prompt_version": "0.1.0", "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    # Step 4: LLM Decision Head (Gemini)
    if router_dec == "NO":
        output = FeatureOutput(
            feature_id=feature.get("feature_id", ""),
            decision="NO",
            confidence=router_conf,
            reasoning_summary="Business geofence detected (see phrasebook cues).",
            evidence=Evidence(feature_spans=[feature.get("feature_description", "")], reg_snippets=[]),
            regulations=[],
            control_type=[],
            metadata=Metadata(retrieval=retrieval_ids, runtime=runtime_info)
        )
        persist_audit(output.model_dump())
        return output.model_dump()

    if router_dec == "YES":
        output = FeatureOutput(
            feature_id=feature.get("feature_id", ""),
            decision="YES",
            confidence=router_conf,
            reasoning_summary="Legal compliance detected (see phrasebook cues).",
            evidence=Evidence(feature_spans=[feature.get("feature_description", "")], reg_snippets=reg_sections[:2]),
            regulations=["UT-SMRA"] if "Utah" in feature.get("feature_description", "") else [],
            control_type=["age_gating"] if any(term in feature.get("feature_description", "").lower() for term in ["minors", "asl", "curfew"]) else [],
            metadata=Metadata(retrieval=retrieval_ids, runtime=runtime_info)
        )
        persist_audit(output.model_dump())
        return output.model_dump()

    # Detector
    detector_prompt = build_detector_prompt(glossary, feature_clauses)
    detector_result = get_gemini_response(detector_prompt)
    detector_json = detector_result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")

    # Policy Mapper
    policymapper_prompt = build_policy_mapper_prompt(feature_clauses, reg_sections)
    policymapper_result = get_gemini_response(policymapper_prompt)
    policymapper_json = policymapper_result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")

    # Arbiter (self-consistency n=3)
    arbiter_outputs = []
    confidences = []
    for _ in range(3):
        arbiter_prompt = build_arbiter_prompt(
            feature.get("feature_id", ""), detector_json, policymapper_json, retrieval_ids, runtime_info)
        arbiter_result = get_gemini_response(arbiter_prompt)
        try:
            arbiter_json = eval(arbiter_result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}"))
            arbiter_outputs.append(arbiter_json)
            confidences.append(arbiter_json.get("confidence", 0.5))
        except Exception:
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
            "reasoning_summary": "Insufficient evidence.",
            "evidence": {"feature_spans": [feature.get("feature_description", "")], "reg_snippets": []},
            "regulations": [],
            "control_type": [],
            "metadata": {"retrieval": retrieval_ids, "runtime": runtime_info}
        }

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
