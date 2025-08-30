import pandas as pd
from src.ai_core import get_ai_analysis, parse_llm_response
from sklearn.metrics import classification_report, confusion_matrix

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
    """Calculates and prints a full classification report."""
    labels = sorted(list(set(y_true + y_pred)))
    report = classification_report(y_true, y_pred, labels=labels)
    print(report)

    print("\n--- Confusion Matrix ---")
    # A confusion matrix helps visualize where the model is making mistakes
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    print(cm_df)

if __name__ == "__main__":
    run_evaluation()