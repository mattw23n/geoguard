#!/usr/bin/env python3
"""
Test script to run GeoGuard classification on sampledata.csv

Processes features from data/sampledata.csv and generates results
"""

import json
import csv
import os
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path for app imports
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from app.decision_head import classify_feature
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the geoguard root directory")
    sys.exit(1)

def load_sample_data():
    """Load sample dataset from CSV file"""
    csv_path = parent_dir / "data" / "sampledata.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Sample dataset not found at {csv_path}")
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    features = []
    
    for idx, row in df.iterrows():
        # Generate feature_id if not present
        feature_id = f"SAMPLE-{idx+1:03d}"
        
        features.append({
            "feature_id": feature_id,
            "feature_name": row["feature_name"],
            "feature_description": row["feature_description"]
        })
    
    return features

def flatten_result_for_csv(result):
    """Convert nested result structure to flat CSV row"""
    return {
        "feature_id": result["feature_id"],
        "feature_name": result.get("feature_name", ""),
        "decision": result["decision"], 
        "confidence": result["confidence"],
        "reasoning_summary": result["reasoning_summary"],
        "regulations": ",".join(result.get("regulations", [])),
        "control_type": ",".join(result.get("control_type", [])),
        "evidence_feature_spans": " | ".join(result.get("evidence", {}).get("feature_spans", [])),
        "evidence_reg_snippets": " | ".join(result.get("evidence", {}).get("reg_snippets", []))
    }

def main():
    """Main execution function"""
    print("🚀 GeoGuard Sample Data Classification Starting...")
    
    try:
        # Load sample dataset
        features = load_sample_data()
        print(f"📋 Loaded {len(features)} features from sampledata.csv")
        
        # Process each feature
        results = []
        for i, feature in enumerate(features, 1):
            print(f"🔄 Processing {i}/{len(features)}: {feature['feature_id']} - {feature['feature_name'][:50]}...")
            try:
                result = classify_feature(feature)
                # Add feature name to result for easier tracking
                result["feature_name"] = feature["feature_name"]
                results.append(result)
                print(f"   ✅ Decision: {result['decision']} (confidence: {result['confidence']:.2f})")
            except Exception as e:
                print(f"   ❌ Error processing {feature['feature_id']}: {e}")
                # Add error result
                results.append({
                    "feature_id": feature["feature_id"],
                    "feature_name": feature["feature_name"],
                    "decision": "ERROR",
                    "confidence": 0.0,
                    "reasoning_summary": f"Processing error: {str(e)}",
                    "evidence": {"feature_spans": [], "reg_snippets": []},
                    "regulations": [],
                    "control_type": [],
                    "metadata": {"retrieval": {}, "runtime": {}}
                })
        
        # Ensure output directory exists
        output_dir = parent_dir / "out"
        output_dir.mkdir(exist_ok=True)
        
        # Write CSV output
        csv_path = output_dir / "sampledata_results.csv"
        csv_results = [flatten_result_for_csv(result) for result in results]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if csv_results:
                writer = csv.DictWriter(f, fieldnames=csv_results[0].keys())
                writer.writeheader()
                writer.writerows(csv_results)
        
        # Write full JSON for debugging/audit
        json_path = output_dir / "sampledata_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Sample Data Test Complete!")
        print(f"📊 Processed: {len(results)} features")
        print(f"📄 CSV Output: {csv_path}")
        print(f"🔍 JSON Output: {json_path}")
        
        # Summary statistics
        decisions = [r["decision"] for r in results]
        print(f"\n📈 Results Summary:")
        for decision_type in ["YES", "NO", "REVIEW", "ERROR"]:
            count = decisions.count(decision_type)
            if count > 0:
                print(f"   {decision_type}: {count}")
        
        # Show some interesting results
        print(f"\n🎯 Sample Results:")
        for result in results[:5]:  # Show first 5
            print(f"   {result['feature_id']}: {result['decision']} ({result['confidence']:.2f}) - {result['feature_name'][:40]}...")
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
