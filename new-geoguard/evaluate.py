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
    ground_truths = df["ground_truth_classification"].tolist()

    print("Running evaluation...")
    for index, row in df.iterrows():
        description = row["feature_description"]
        print(f"  Testing item {index + 1}/{len(df)}...")
        raw_response = get_ai_analysis(description)
        parsed_response = parse_llm_response(raw_response)
        predictions.append(parsed_response["classification"])

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