import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
from sklearn.metrics import classification_report, confusion_matrix

# Load environment variables FIRST before importing modules that need them
load_dotenv()

from src.ai_core import get_ai_analysis, parse_llm_response

TEST_DATA_PATH = "../sample-dataset/sample_data.csv"
RESULTS_OUTPUT_PATH = "../sample-dataset/sample_data_results.csv"

# SPECIFIC TEST CASES TO RUN (1-indexed)
# Leave empty [] to run all test cases
# Example: [1, 3, 5] to run only test cases 1, 3, and 5
SPECIFIC_TEST_CASES = [16,19,20,21,22,23,24,25,26,27,28,29,30]


def run_evaluation():
    """Runs the AI analysis on the test dataset and saves results."""
    try:
        df = pd.read_csv(TEST_DATA_PATH)
    except FileNotFoundError:
        print(f"Error: Test data file not found at {TEST_DATA_PATH}")
        return

    predictions = []
    detailed_results = []

    # Filter test cases if specific ones are requested
    if SPECIFIC_TEST_CASES:
        # Convert to 0-indexed for pandas
        test_indices = [i - 1 for i in SPECIFIC_TEST_CASES if 1 <= i <= len(df)]
        df_filtered = df.iloc[test_indices].reset_index(drop=True)
        print(f"Running specific test cases: {SPECIFIC_TEST_CASES}")
        print(f"Total test cases to run: {len(df_filtered)}")
    else:
        df_filtered = df
        print(f"Running all test cases: {len(df_filtered)}")

    print("Note: Using sample data without ground truth labels - running AI analysis only\n")

    for index, row in df_filtered.iterrows():
        # Calculate original test case number
        if SPECIFIC_TEST_CASES:
            original_case_num = SPECIFIC_TEST_CASES[index]
        else:
            original_case_num = index + 1
            
        print(f"[*] Running test case {original_case_num}: '{row['feature_name']}'")

        # Use the feature description for analysis
        full_feature_text = f"""
        Feature Name: {row['feature_name']}
        Feature Description: {row['feature_description']}
        """

        # Use the AI analysis
        raw_response = get_ai_analysis(full_feature_text)
        parsed_response = parse_llm_response(raw_response)
        predicted = parsed_response["classification"]
        predictions.append(predicted)

        print(f"  -> Predicted: {predicted}")
        print(f"  -> Reasoning: {parsed_response.get('reasoning', 'No reasoning provided')[:100]}...")
        print(f"  -> Regulation: {parsed_response.get('regulation', 'None')}\n")

        # Collect detailed results for CSV output
        detailed_results.append({
            "test_case_id": original_case_num,
            "feature_name": row['feature_name'],
            "feature_description": row['feature_description'],
            "predicted_classification": predicted,
            "confidence": parsed_response.get("confidence", 0.0),
            "reasoning": parsed_response.get("reasoning", ""),
            "regulation": parsed_response.get("regulation", "None"),
            "triggered_rules": str(parsed_response.get("triggered_rules", [])),
            "recommendations": str(parsed_response.get("recommendations", []))
        })

    # Save detailed results to CSV
    results_df = pd.DataFrame(detailed_results)
    
    # Add timestamp and summary statistics
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Count classifications
    classification_counts = {}
    for pred in predictions:
        classification_counts[pred] = classification_counts.get(pred, 0) + 1
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(RESULTS_OUTPUT_PATH), exist_ok=True)
    
    # Save results
    results_df.to_csv(RESULTS_OUTPUT_PATH, index=False)
    
    print(f"\n--- Results saved to {RESULTS_OUTPUT_PATH} ---")
    print(f"Timestamp: {timestamp}")
    print(f"Total test cases: {len(detailed_results)}")
    print(f"Classification breakdown:")
    for classification, count in classification_counts.items():
        percentage = (count / len(predictions)) * 100
        print(f"  {classification}: {count} ({percentage:.1f}%)")
    print()

def calculate_metrics(y_true, y_pred):
    """Calculates and prints a full classification report."""
    labels = sorted(list(set(y_true + y_pred)))
    report = classification_report(y_true, y_pred, labels=labels, zero_division=0)
    print(report)

    print("\n--- Confusion Matrix ---")
    # A confusion matrix helps visualize where the model is making mistakes
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in labels], columns=[f"Pred_{l}" for l in labels])
    print(cm_df)

if __name__ == "__main__":
    run_evaluation()