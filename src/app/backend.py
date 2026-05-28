# Import standard library packages.
import pickle

# Import third party packages.
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox, QWidget

# Import local packages.
from src.models.random_forest_baseline import RandomForestBaseline


class _ModelUnpickler(pickle.Unpickler):
    """
    Unpickler that maps legacy model pickles created from script execution.
    """

    def find_class(self, module: str, name: str) -> object:
        if module == "__main__" and name == "RandomForestBaseline":
            return RandomForestBaseline

        return super().find_class(module, name)


def run_agent_pipeline(
    window: QWidget, required_index: float, df: pd.DataFrame
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
    # Load the model.
    try:
        with open("models/model.pkl", "rb") as file:
            saved = _ModelUnpickler(file).load()

    except FileNotFoundError:
        QMessageBox.warning(
            window,
            "File not found",
            "The ML model .pkl file could not be found.",
        )
        return

    except (AttributeError, EOFError, pickle.UnpicklingError) as error:
        QMessageBox.warning(
            window,
            "Invalid model file",
            f"The ML model .pkl file could not be loaded: {error}",
        )
        return

    model_type = saved["model_type"]
    model = saved["model"]
    feature_cols = saved["feature_cols"]
    engineer_features = saved.get("engineer_features")

    # Split the data into each loading condition so we can get model output for each loading condition.
    X = df.select_dtypes(include=["number"])
    if "condition_code" in X.columns:
        X = (
            X[X["condition_code"].isin([0, 1, 2])]
            .sort_values("condition_code")
            .drop_duplicates("condition_code", keep="first")
        )
    else:
        X = X.head(3)

    if engineer_features is not None:
        X = engineer_features(X)
    X = X[feature_cols]

    # Predict based on the model type - once a single performing model is selected, this can be narrowed down.
    predictions = []
    confidence_intevals = []
    if model_type == "MAPIE XGB Regressor":
        model_predictions, intervals = model.predict_interval(X)
        predictions = model_predictions.ravel().tolist()
        confidence_intevals = [
            (float(lower), float(upper)) for lower, upper in intervals[:, :, 0]
        ]

    else:
        # Get per-tree predictions and calculate the 95% CI to display confidence.
        X_values = X.to_numpy()
        all_tree_preds = np.array(
            [tree.predict(X_values) for tree in model.estimators_]
        )
        predictions = np.mean(all_tree_preds, axis=0).tolist()
        lower_bounds = np.percentile(all_tree_preds, 2.5, axis=0)
        upper_bounds = np.percentile(all_tree_preds, 97.5, axis=0)
        confidence_intevals = list(zip(lower_bounds.tolist(), upper_bounds.tolist()))

    # Get the pass results for each prediction, for each loading condition.
    # The minimum value for each condition is 0.5 * R.
    pass_results = [
        "Pass" if prediction >= required_index * 0.5 else "Fail"
        for prediction in predictions
    ]

    return predictions, confidence_intevals, pass_results
