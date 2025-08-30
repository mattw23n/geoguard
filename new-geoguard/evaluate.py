import pandas as pd
from src.ai_core import get_ai_analysis, parse_llm_response

TEST_DATA_PATH = "data/test_data.csv"


def run_evaluation():
    """Runs the AI analysis on the test dataset and prints performance metrics."""
    try:
        df = pd.read_csv(TEST_DATA_PATH)
    except FileNotFoundError:
        print(f"Error: Test data file not found at {TEST_DATA_PATH}")
        return

    predictions = []
    # CHANGED: Use the "ground_truth" column from our new CSV file
    ground_truths = df["ground_truth"].tolist()

    print(f"Starting evaluation with {len(df)} test cases...\n")

    for index, row in df.iterrows():
        print(f"[*] Running test case {index + 1}: '{row['feature_title']}'")

        # CHANGED: Combine all feature details to give the AI full context, as per feedback.
        full_feature_text = f"""
        Feature Title: {row['feature_title']}
        Feature Description: {row['feature_description']}
        Product Requirements Doc: {row['feature_prd']}
        Technical Requirements Doc: {row['feature_trd']}
        """

        # Use the combined text for analysis
        raw_response = get_ai_analysis(full_feature_text)
        parsed_response = parse_llm_response(raw_response)
        predicted = parsed_response["classification"]
        predictions.append(predicted)
        
        expected = row["ground_truth"]

        # ADDED: Print the result for each test case, as per your friend's feedback.
        is_correct = "✅" if (expected == predicted) else "❌"
        print(f"  -> Expected: {expected:<7} | Predicted: {predicted:<7} | Result: {is_correct}\n")


    print("\n--- Evaluation Results ---")
    calculate_metrics(ground_truths, predictions)


def calculate_metrics(y_true, y_pred):
    """Calculates and prints accuracy, precision, recall, and F1-score."""
    # Accuracy
    correct = sum(1 for true, pred in zip(y_true, y_pred) if true == pred)
    accuracy = correct / len(y_true)
    print(f"Accuracy: {accuracy:.2f}")

    # Metrics for the "YES" class (the most important one)
    tp = sum(1 for true, pred in zip(y_true, y_pred) if true == "YES" and pred == "YES")
    fp = sum(1 for true, pred in zip(y_true, y_pred) if true != "YES" and pred == "YES")
    fn = sum(1 for true, pred in zip(y_true, y_pred) if true == "YES" and pred != "YES")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    print(f"\nMetrics for the 'YES' class:")
    print(f"  Precision: {precision:.2f}")
    print(f"  Recall:    {recall:.2f}")
    print(f"  F1-Score:  {f1_score:.2f}")

if __name__ == "__main__":
    run_evaluation()