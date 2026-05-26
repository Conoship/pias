# Import standard library packages.
import pickle

# Import third party packages.
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox, QWidget

# Import local packages.
from src.models.random_forest_baseline import RandomForestBaseline  # noqa: F401


# TODO: Modify this function to return one prediction, CI and pass result per loading condition.
def run_agent_pipeline(
    window: QWidget, required_index: float, df_final: pd.DataFrame
) -> tuple[list[float], list[tuple[float, float]], list[str]] | None:
    """
    Execute the AI agent pipeline: load data, run the trained model,
    and return the predicted results.

    Args:
        window (QWidget):
            The main application window.

        required_index (float):
            The Required Index (R) value required for the ship to pass according to the SOLAS requirements.

        df_final (pd.DataFrame):
            The df containing the the concatened data frames from the other parsers and the user defined values.

    Returns:
        tuple[list[float], list[tuple[float, float]], list[str]]:
            A tuple containing the lists of predictions, 95% CIs and the A against R comparison result (one element per loading condition)
    """
    # If we use just mock data:
    # df = pd.read_csv("./mockdata.csv")

    # If we use user input:
    df = df_final

    # Load the model.
    try:
        with open("models/model.pkl", "rb") as file:
            saved = pickle.load(file)

    except FileNotFoundError:
        QMessageBox.warning(
            window,
            "File not found",
            "The ML model .pkl file could not be found.",
        )
        return

    model_type = saved["model_type"]
    model = saved["model"]
    feature_cols = saved["feature_cols"]
    engineer_features = saved.get("engineer_features")

    # Feed the data to the model and get the results.
    X = df.select_dtypes(include=["number"])
    if engineer_features is not None:
        X = engineer_features(X)
    X = X[feature_cols]

    # TODO: Training data, X has 3 rows, one per condition => split data into X_light, X_partial and X_deepest to predict an Attained Index (A) for each one of them.

    # Predict based on the model type - once a single performing model is selected, this can be narrowed down.
    predictions = []
    confidence_intevals = []
    if model_type == "MAPIE XGB Regressor":
        model_predictions, intervals = model.predict_interval(X)
        prediction = model_predictions[0].item()
        predictions.append(prediction)
        lower = float(intervals[0, 0, 0].item())
        upper = float(intervals[0, 1, 0].item())
        confidence_intevals.append((lower, upper))

    else:
        # Get per-tree predictions and calculate the 95% CI to display confidence.
        X_values = X.to_numpy()
        all_tree_preds = np.array(
            [tree.predict(X_values) for tree in model.estimators_]
        )
        prediction = np.mean(all_tree_preds, axis=0)[0].item()
        predictions.append(prediction)
        lower = np.percentile(all_tree_preds, 2.5, axis=0)[0].item()
        upper = np.percentile(all_tree_preds, 97.5, axis=0)[0].item()
        confidence_intevals.append((lower, upper))

    # Get the pass results for each prediction, for each loading condition.
    # The minimum value for each condition is 0.5 * R.
    pass_results = [
        "Pass" if prediction >= required_index * 0.5 else "Fail"
        for prediction in predictions
    ]

    return predictions, confidence_intevals, pass_results
