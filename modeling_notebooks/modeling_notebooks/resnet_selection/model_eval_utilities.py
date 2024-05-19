import pandas as pd


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

            # Compute the confusion matrix
            model_df["prediction"] = model_df[score_colname] > threshold
            confusion_matrix = pd.crosstab(
                model_df[true_category_colname], model_df["prediction"]
            )

            # Compute the true positive rate, false positive rate, precision, and recall
            true_positive = confusion_matrix.loc[True, True]
            false_positive = confusion_matrix.loc[False, True]
            false_negative = confusion_matrix.loc[True, False]

            true_positive_rate = true_positive / (true_positive + false_negative)
            false_positive_rate = false_positive / (
                false_positive + confusion_matrix.loc[False, False]
            )

            precision = true_positive / (true_positive + false_positive)
            recall = true_positive / (true_positive + false_negative)

            metric_results_records.append(
                {
                    "model_name": model_name,
                    "threshold": threshold,
                    "true_positive_count": true_positive,
                    "false_positive_count": false_positive,
                    "true_positive_rate": true_positive_rate,
                    "false_positive_rate": false_positive_rate,
                    "precision": precision,
                    "recall": recall,
                }
            )

    return pd.DataFrame.from_records(metric_results_records)
