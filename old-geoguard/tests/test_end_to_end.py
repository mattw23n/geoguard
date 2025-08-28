from app.decision_head import classify_feature

def test_positive():
    payload = {
        "feature_id": "F-001",
        "feature_name": "Curfew login blocker with ASL",
        "feature_description": "To comply with the Utah Social Media Regulation Act, we implement a curfew-based login restriction for minors."
    }
    result = classify_feature(payload)
    assert result["decision"] == "YES"
    assert "UT-SMRA" in result["regulations"] or result["decision"] == "REVIEW"

def test_negative():
    payload = {
        "feature_id": "F-002",
        "feature_name": "South Korea dark theme A/B experiment",
        "feature_description": "A/B test dark theme accessibility for users in South Korea. Rollout is limited via GH and monitored with FR flags."
    }
    result = classify_feature(payload)
    assert result["decision"] == "NO"

def test_ambiguous():
    payload = {
        "feature_id": "F-003",
        "feature_name": "A video filter available globally except KR",
        "feature_description": "Feature is available in all regions except Korea; no legal rationale stated."
    }
    result = classify_feature(payload)
    assert result["decision"] == "REVIEW"
