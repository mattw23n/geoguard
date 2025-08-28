#!/usr/bin/env python3
"""
Test script to verify LLM classification is working
"""

import sys
from pathlib import Path

# Add parent directory to path for app imports
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from app.decision_head import classify_feature

def test_llm_classification():
    print("🧪 Testing LLM Classification")
    print("=" * 50)
    
    # Test feature that should trigger LLM
    test_feature = {
        "feature_id": "TEST-001",
        "feature_name": "Utah Curfew Login Blocker",
        "feature_description": "To comply with the Utah Social Media Regulation Act, we implement a curfew-based login restriction for minors using ASL detection."
    }
    
    print(f"Testing feature: {test_feature['feature_name']}")
    print(f"Description: {test_feature['feature_description']}")
    print("\n🚀 Running classification...")
    
    try:
        result = classify_feature(test_feature)
        
        print("\n✅ Classification Results:")
        print(f"Feature ID: {result['feature_id']}")
        print(f"Decision: {result['decision']}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Reasoning: {result['reasoning_summary']}")
        print(f"Regulations: {result.get('regulations', [])}")
        print(f"Control Types: {result.get('control_type', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_classification()
    if success:
        print("\n🎉 LLM classification test passed!")
    else:
        print("\n💥 LLM classification test failed!")
        sys.exit(1)
