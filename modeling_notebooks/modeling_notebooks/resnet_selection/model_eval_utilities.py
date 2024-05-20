import pandas as pd
from sklearn.metrics import confusion_matrix


def generate_metric_curves(
    df: pd.DataFrame,
    model_colname: str = "model_name",
    true_category_colname: str = "category",
    score_colname: str = "score",
    breaks: int = 100,
) -> pd.DataFrame:
    """
    Generate a DataFrame with the ROC and PR curves for each model.

    Yes, I know that scikit-learn has utilities for this, but thoe utilities don't
    provide the flexibility I would like for this project.

    Args:
        df: DataFrame containing the true category and the score for the predicted category.
        true_category_colname: Column name for the true category.
        score_colname: Column name for the predicted category score.

    Returns:
        DataFrame with the ROC and PR curves.
    """
    # Code to generate the ROC and PR curves

    metric_results_records = []

    for model_name in df[model_colname].unique():
        model_df = df[df[model_colname] == model_name].copy()

        for i in range(breaks + 1):

            threshold = i / breaks
            model_df["prediction"] = model_df[score_colname] > threshold
            cm = confusion_matrix(
                y_true=model_df[true_category_colname],
                y_pred=model_df["prediction"],
                labels=[True, False],
            )

            # Compute the true positive rate, false positive rate, precision, and recall
            true_positive = cm[0, 0]
            false_positive = cm[1, 0]
            true_negative = cm[1, 1]
            false_negative = cm[0, 1]
            positive_count = true_positive + false_negative
            negative_count = false_positive + true_negative
            positive_prediction_count = true_positive + false_positive

            true_positive_rate = (
                true_positive / positive_count if positive_count > 0 else 0
            )
            false_positive_rate = (
                false_positive / negative_count if negative_count > 0 else 0
            )

            precision = (
                true_positive / positive_prediction_count
                if positive_prediction_count > 0
                else 0
            )
            recall = true_positive_rate

            metric_results_records.append(
                {
                    "model_name": model_name,
                    "threshold": threshold,
                    "true_positive_count": true_positive,
                    "false_positive_count": false_positive,
                    "true_negative_count": true_negative,
                    "false_negative_count": false_negative,
                    "true_positive_rate": true_positive_rate,
                    "false_positive_rate": false_positive_rate,
                    "precision": precision,
                    "recall": recall,
                }
            )

    return pd.DataFrame.from_records(metric_results_records)
