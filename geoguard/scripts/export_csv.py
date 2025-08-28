# Batch inference and CSV export
import pandas as pd
import os
import sys
sys.path.append('.')
from app.decision_head import classify_feature

def main():
    df = pd.read_csv("data/synthetic.csv")
    results = []
    for _, row in df.iterrows():
        result = classify_feature(row.to_dict())
        results.append(result)
    
    # Ensure output directory exists
    os.makedirs("out", exist_ok=True)
    out_df = pd.DataFrame(results)
    out_df.to_csv("out/geoguard_results.csv", index=False)
    print(f"✅ Results exported to out/geoguard_results.csv")
    print(f"📊 Processed {len(results)} features")

if __name__ == "__main__":
    main()
