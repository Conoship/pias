# Import standard library packages.
import os
import pickle

# Import third party packages.
from dotenv import load_dotenv
import numpy as np
import pandas as pd

# Import local packages.
from src.models.random_forest_baseline import RandomForestBaseline

load_dotenv()


# TODO: Modify this function to return one prediction per loading condition.
def run_agent_pipeline(
    pass_value: float, df_final: pd.DataFrame
) -> tuple[list[float], float, float, str]:
    """
    Execute the AI agent pipeline: load data, run the trained model,
    and return the predicted results.

    Args:
        window (QWidget):
            The main application window used to locate UI elements
            where results will be displayed.
    """

    # If we use just mock data:
    # df = pd.read_csv("./mockdata.csv")

    # If we use user input:
    df = df_final

    # Load the model.
    with open("models/model.pkl", "rb") as file:
        saved = pickle.load(file)

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
