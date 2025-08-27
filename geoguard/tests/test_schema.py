from app.schema import FeatureOutput, Evidence, Metadata

def test_schema_valid():
    evidence = Evidence(feature_spans=["test"], reg_snippets=["reg snippet"])
    metadata = Metadata(retrieval={"feature_clause_ids": ["f:1"]}, runtime={"pipeline_version": "0.1.0"})
    output = FeatureOutput(
        feature_id="F-001",
        decision="YES",
        confidence=0.9,
        reasoning_summary="Test summary",
        evidence=evidence,
        regulations=["DSA"],
        control_type=["age_gating"],
        metadata=metadata
    )
    assert output.decision in ["YES", "NO", "REVIEW"]
    assert 0.0 <= output.confidence <= 1.0
    assert isinstance(output.evidence.feature_spans, list)
    assert isinstance(output.evidence.reg_snippets, list)
    assert isinstance(output.regulations, list)
    assert isinstance(output.control_type, list)
