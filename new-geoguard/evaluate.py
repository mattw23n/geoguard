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
    # CHANGED: Use the "ground_truth" column from our new CSV file
    ground_truths = df["ground_truth"].tolist()

    print(f"Starting evaluation with {len(df)} test cases...\n")

    for index, row in df.iterrows():
        print(f"[*] Running test case {index + 1}: '{row['feature_title']}'")

        # CHANGED: Combine all feature details to give the AI full context, as per your friend's feedback.
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

        # ADDED: Print the result for each test case, as per feedback.
        is_correct = "✅" if (expected == predicted) else "❌"
        print(f"  -> Expected: {expected:<7} | Predicted: {predicted:<7} | Result: {is_correct}\n")


    print("\n--- Evaluation Results ---")
    calculate_metrics(ground_truths, predictions)

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