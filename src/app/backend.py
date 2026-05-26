# Import standard library packages.
import pickle

# Import third party packages.
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox, QWidget

# Import local packages.
from src.models.random_forest_baseline import RandomForestBaseline  # noqa: F401


# TODO: Modify this function to return one prediction per loading condition.
def run_agent_pipeline(
    window: QWidget, pass_value: float, df_final: pd.DataFrame
) -> tuple[list[float], float, float, str] | None:
    """
    Execute the AI agent pipeline: load data, run the trained model,
    and return the predicted results.

    Args:
        pass_value (float):
            The Required Index (R) value required for the ship to pass according to the SOLAS requirements.

        df_final (pd.DataFrame):
            The df containing the the concatened data frames from the other parsers and the user defined values.

    Returns:
        tuple[list[float], float, float, str] | None:
            A tuple containing the list of predictions (one per loading condition),
            the lower and the upper bounds of the 95% CI and lastly the A against R comparison result.
            Returns `None` if the `.pkl` file was not found.
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

    # Predict based on the model type - once a single performing model is selected, this can be narrowed down.
    lower, upper = -1, -1
    predictions = []
    if model_type == "MAPIE XGB Regressor":
        model_predictions, intervals = model.predict_interval(X)
        prediction = model_predictions[0].item()
        lower = float(intervals[0, 0, 0].item())
        upper = float(intervals[0, 1, 0].item())

    else:
        # Get per-tree predictions and calculate the 95% CI to display confidence.
        X_values = X.to_numpy()
        all_tree_preds = np.array(
            [tree.predict(X_values) for tree in model.estimators_]
        )
        prediction = np.mean(all_tree_preds, axis=0)[0].item()
        lower = np.percentile(all_tree_preds, 2.5, axis=0)[0].item()
        upper = np.percentile(all_tree_preds, 97.5, axis=0)[0].item()

    if prediction >= pass_value:
        pass_result = "A is above the required index R"
    else:
        pass_result = "A is below the required index R"

    return predictions, lower, upper, pass_result
