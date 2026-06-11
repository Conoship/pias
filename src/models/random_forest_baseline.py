# Import standard library packages.
from typing import Any

# Import third party packages.
import os
import yaml
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    max_error,
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
)
from sklearn.model_selection import GroupKFold, learning_curve

from src.features.feature_sets import (
    DEFAULT_FEATURE_SET,
    select_feature_columns,
)


class RandomForestBaseline(object):
    # The name of the target hyperparameter configuration.
    _CONFIG_NAME = "RandomForestRegressor"

    # The name of the secondary hyperparameter configuration.
    _LOW_IMPACT_CONFIG_NAME = "LowImpactRandomForestRegressor"

    # The columns of the dataset to use exclude from the features (X).
    _COLS_TO_DROP = [
        "target_margin",
        "target_attained_index",
        "ship_version_id",
        "condition_code",
        "subdivision_length",
    ]

    # The column of the dataset to use as label (Y).
    _Y_LABEL = "target_attained_index"

    # The YAML feature set to use when src/models/features.yaml is present.
    _FEATURE_SET_NAME = DEFAULT_FEATURE_SET

    # The column by which we create the groups for K-Fold Cross-Validation.
    _GROUP_BY = "ship_id"

    # The number of splits for K-Fold Cross-Validation
    _K_FOLD_CROSS_SPLITS = 5

    def __init__(self, path_to_config: str, path_to_data: str) -> None:
        """
        Random Forest Regressor Baseline Model.

        Args:
            path_to_config (str):
                The path to the `config.yaml` containing the model hyperparameters.

            path_to_data (str):
                The path to the `.csv` file containing the training data for the model.
        """
        # Get constructor arguments.
        self.path_to_config = path_to_config
        self.path_to_data = path_to_data

        # Lists to hold results.
        self.mae_scores = []
        self.rmse_scores = []
        self.median_absolute_error_scores = []
        self.max_error_scores = []
        self.bias_scores = []
        self.fold_results = []

        # The index of the best performing fold.
        self.best_fold = 0

    def _load_data(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        """
        Load the data from the CSV into a Pandas DataFrame and get X and Y.

        Returns:
            df, X, Y (tuple): A tuple containing the Pandas DataFrame, X and Y
        """
        df = pd.read_csv(self.path_to_data)
        feature_cols = select_feature_columns(
            df,
            feature_set_name=self._FEATURE_SET_NAME,
            fallback_drop_columns=self._COLS_TO_DROP,
        )
        X = df[feature_cols]
        Y = df[self._Y_LABEL]

        return df, X, Y

    def _load_config(self, config_name: str) -> dict[str, Any]:
        """
        Load the hyperparameters configuration for the specific model.
        This method uses the constructor argument `path_to_config`.

        Args:
            config_name (str):
                The name of the config to load.
        """
        config = {}
        with open(self.path_to_config, "r") as f:
            config = yaml.safe_load(f)

        return config[config_name]

    def _save_model(
        self, model: RandomForestRegressor, feature_cols: list[str]
    ) -> None:
        """
        Save the model as a .pkl binary file.

        Args:
            model (RandomForestRegressor):
                The Random Forest Regressor model to save as the .pkl file.

            feature_cols (list[str]):
                A list of all the columns the model is using as features to train on.
        """
        with open("models/model_partial.pkl", "wb") as file:
            pickle.dump(
                {
                    "model_type": "Random Forest Regressor",
                    "model": model,
                    "feature_cols": feature_cols,
                    "engineer_features": self._engineer_features,
                },
                file,
            )

    def _print_results(self) -> None:
        """
        Print the final accuracy results of the training.
        """
        print(f"Model Performance")
        print(f"Mean MAE: {sum(self.mae_scores) / len(self.mae_scores):.4f}")
        print(f"Mean RMSE: {sum(self.rmse_scores) / len(self.rmse_scores):.4f}")
        print(
            "Mean median absolute error: "
            f"{sum(self.median_absolute_error_scores) / len(self.median_absolute_error_scores):.4f}"
        )
        print(f"Mean max error: {sum(self.max_error_scores) / len(self.max_error_scores):.4f}")
        print(f"Mean bias: {sum(self.bias_scores) / len(self.bias_scores):.4f}")

    def _calculate_accuracy_metrics(
        self, y_true: pd.Series, predictions: np.ndarray
    ) -> dict[str, float]:
        errors = predictions - y_true.to_numpy()

        return {
            "mae": mean_absolute_error(y_true, predictions),
            "rmse": float(np.sqrt(mean_squared_error(y_true, predictions))),
            "median_absolute_error": median_absolute_error(y_true, predictions),
            "max_error": max_error(y_true, predictions),
            "bias": float(np.mean(errors)),
        }

    def _filter_low_impact_features(
        self, X: pd.DataFrame, Y: pd.Series
    ) -> pd.DataFrame:
        low_impact_random_forest_params = self._load_config(
            self._LOW_IMPACT_CONFIG_NAME
        )
        temp_rf = RandomForestRegressor(**low_impact_random_forest_params).fit(X, Y)
        important_cols = X.columns[temp_rf.feature_importances_ > 0.01]
        X = X[important_cols]

        return X

    def _engineer_features(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        # Displacement-to-length ratio: normalizes displacement by ship size.
        if "displacement" in X.columns and "total_layout_length" in X.columns:
            X["displacement_per_length"] = X["displacement"] / X["total_layout_length"]

        # VCG-to-height ratio: how high the centre of gravity is relative to ship height.
        if "vcg" in X.columns and "max_layout_height" in X.columns:
            X["vcg_to_height_ratio"] = X["vcg"] / X["max_layout_height"]

        # Draft-to-height ratio: loading depth relative to ship height.
        if "draft" in X.columns and "max_layout_height" in X.columns:
            X["draft_to_height_ratio"] = X["draft"] / X["max_layout_height"]

        # Openings exposure: openings scaled by compartment count.
        if (
            "openings_per_compartment" in X.columns
            and "total_compartments" in X.columns
        ):
            X["total_openings"] = (
                X["openings_per_compartment"] * X["total_compartments"]
            )

        # Void ratio: void compartments as a fraction of total.
        if "n_void" in X.columns and "total_compartments" in X.columns:
            X["void_ratio"] = X["n_void"] / X["total_compartments"]

        # Ballast ratio: same for ballast.
        if "n_ballast" in X.columns and "total_compartments" in X.columns:
            X["ballast_ratio"] = X["n_ballast"] / X["total_compartments"]

        return X

    def train(self) -> None:
        """
        Train models for each fold and store them internally.
        """
        # Load Data.
        df, X, Y = self._load_data()
        groups = df[self._GROUP_BY]

        # Clear previous results.
        self.fold_results.clear()

        # Filter out low impact features.
        # X = self._engineer_features(X)
        # X = self._filter_low_impact_features(X, Y)

        # Cross-validation.
        gkf = GroupKFold(n_splits=self._K_FOLD_CROSS_SPLITS)
        ranfom_forest_params = self._load_config(self._CONFIG_NAME)
        for train_idx, test_idx in gkf.split(X, Y, groups=groups):
            # Train Data.
            x_train = X.iloc[train_idx]
            y_train = Y.iloc[train_idx]

            # Test Data.
            x_test = X.iloc[test_idx]
            y_test = Y.iloc[test_idx]

            # Train model.
            model = RandomForestRegressor(**ranfom_forest_params)
            model.fit(x_train, y_train)

            # Store everything needed for evaluation.
            self.fold_results.append(
                {
                    "model": model,
                    "x_test": x_test,
                    "y_test": y_test,
                }
            )

    def evaluate(
        self, save_best_model: bool = False, print_results: bool = False
    ) -> None:
        """
        Evaluate all trained fold models.

        Raises:
            ValueError:
                If the list `self.fold_results` is empty and therefore the model was not trained.

        Args:
            save_best_model (bool, optional):
                Boolean flag to enable the user to save the best performing model
                by comparing in each fold the accuracy to the previous fold accuracy.
                Defaults to `False`.

            print_training_results (bool, optional):
                Boolean flag to enable logging and print to the console the results of
                each training fold and the average accuracy metrics of the model after the training
                is completed. Defaults to `False`.
        """
        if not self.fold_results:
            raise ValueError("No trained models found. Call train() first.")

        self.mae_scores.clear()
        self.rmse_scores.clear()
        self.median_absolute_error_scores.clear()
        self.max_error_scores.clear()
        self.bias_scores.clear()
        best_mae = float("inf")
        for fold, result in enumerate(self.fold_results):
            # Get data from each fold.
            model = result["model"]
            x_test = result["x_test"]
            y_test = result["y_test"]

            # Make predictions and calculate accuracy metrics.
            predictions = model.predict(x_test)
            metrics = self._calculate_accuracy_metrics(y_test, predictions)

            # Append to the lists.
            self.mae_scores.append(metrics["mae"])
            self.rmse_scores.append(metrics["rmse"])
            self.median_absolute_error_scores.append(metrics["median_absolute_error"])
            self.max_error_scores.append(metrics["max_error"])
            self.bias_scores.append(metrics["bias"])

            # Save the fold with the lowest typical absolute error.
            if save_best_model and metrics["mae"] < best_mae:
                self._save_model(model, list(x_test.columns))
                best_mae = metrics["mae"]
                self.best_fold = fold

            # Print fold results if needed.
            if print_results:
                print(f"Fold {fold + 1}")
                print(f"MAE: {metrics['mae']:.4f}")
                print(f"RMSE: {metrics['rmse']:.4f}")
                print(f"Median absolute error: {metrics['median_absolute_error']:.4f}")
                print(f"Max error: {metrics['max_error']:.4f}")
                print(f"Bias: {metrics['bias']:.4f}")

        if print_results:
            self._print_results()

    def _get_eval_data(self) -> tuple[
        RandomForestRegressor,
        pd.DataFrame,
        pd.Series,
        np.ndarray,
    ]:
        """
        Get the best fold results to use for plot.

        Raises:
            ValueError:
                If the list `self.fold_results` is empty and therefore the model was not trained.

        Returns:
            model, x_test, y_test, preds (tuple):
                Returns the above tuple, that has data that are being used by the plotting methods.
        """
        if not self.fold_results:
            raise ValueError("No trained models found. Call train() first.")

        result = self.fold_results[self.best_fold]
        model = result["model"]
        x_test = result["x_test"]
        y_test = result["y_test"]
        preds = model.predict(x_test)

        return model, x_test, y_test, preds

    def plot_pred_vs_actual(
        self,
        save: bool = True,
        output_dir: str = "plots",
        tolerance: float = 0.02,
    ) -> None:
        """
        Plot the actual vs the predicted values of the features.

        Args:
            save (bool, optional):
                If the generated plots should be saved. Defaults to True.

            output_dir (str, optional):
                Where the generated plots should be saved. Defaults to "plots".

            tolerance (float, optional):
                Acceptable absolute prediction error to highlight. Defaults to 0.02.
        """
        # Get the data and calculate accuracy metrics.
        _, _, y_test, preds = self._get_eval_data()
        metrics = self._calculate_accuracy_metrics(y_test, preds)
        abs_errors = np.abs(preds - y_test.to_numpy())
        within_tolerance = float(np.mean(abs_errors <= tolerance) * 100.0)

        # Plot the data.
        plt.figure(figsize=(8, 6))
        plt.scatter(y_test, preds, alpha=0.6)

        axis_min = min(y_test.min(), preds.min())
        axis_max = max(y_test.max(), preds.max())
        plt.plot(
            [axis_min, axis_max],
            [axis_min, axis_max],
            "k--",
            label="Perfect prediction",
        )
        plt.fill_between(
            [axis_min, axis_max],
            [axis_min - tolerance, axis_max - tolerance],
            [axis_min + tolerance, axis_max + tolerance],
            color="green",
            alpha=0.12,
            label=f"Within +/- {tolerance:.3f}",
        )

        if len(y_test) > 1:
            slope, intercept = np.polyfit(y_test, preds, 1)
            best_fit = slope * np.array([axis_min, axis_max]) + intercept
            plt.plot(
                [axis_min, axis_max],
                best_fit,
                "r:",
                linewidth=2,
                label="Best fit",
            )

        plt.text(
            0.05,
            0.9,
            "MAE: {mae:.4f}\nMedian AE: {medae:.4f}\nWithin +/- {tol:.3f}: {within:.1f}%".format(
                mae=metrics["mae"],
                medae=metrics["median_absolute_error"],
                tol=tolerance,
                within=within_tolerance,
            ),
            transform=plt.gca().transAxes,
            bbox=dict(facecolor="white", alpha=0.7),
        )
        plt.title("Predicted vs Actual")
        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        plt.xlim(axis_min, axis_max)
        plt.ylim(axis_min, axis_max)
        plt.gca().set_aspect("equal", adjustable="box")
        plt.legend()
        plt.tight_layout()

        # Save the plots if necessary.
        if save:
            os.makedirs(output_dir, exist_ok=True)
            plt.savefig(f"{output_dir}/pred_vs_actual.png")

        plt.show()

    def plot_residuals(self, save: bool = True, output_dir: str = "plots") -> None:
        """
        Plot the residuals.

        Args:
            save (bool, optional):
                If the generated plots should be saved. Defaults to True.

            output_dir (str, optional):
                Where the generated plots should be saved. Defaults to "plots".
        """
        # Get the data and calculate the residuals.
        _, _, y_test, preds = self._get_eval_data()
        errors = preds - y_test
        mean_error = errors.mean()

        # Plot the data.
        plt.figure(figsize=(8, 6))
        plt.scatter(preds, errors, alpha=0.6)
        plt.axhline(0, color="black")
        plt.axhline(mean_error, color="red", linestyle="--", label="Mean error")
        plt.title("Residuals")
        plt.xlabel("Predicted")
        plt.ylabel("Prediction error")
        plt.legend()
        plt.tight_layout()

        # Save the plots if necessary.
        if save:
            os.makedirs(output_dir, exist_ok=True)
            plt.savefig(f"{output_dir}/residuals.png")

        plt.show()

    def plot_learning_curve(self, save: bool = True, output_dir: str = "plots") -> None:
        """
        Plot the model's learning curve.

        Args:
            save (bool, optional):
                If the generated plots should be saved. Defaults to True.

            output_dir (str, optional):
                Where the generated plots should be saved. Defaults to "plots".
        """
        # Load the data.
        _, X, Y = self._load_data()
        X = self._engineer_features(X)

        # Create the model to get the learning curve parameters.
        random_forest_params = self._load_config(self._CONFIG_NAME)
        model = RandomForestRegressor(**random_forest_params)
        train_sizes, train_scores, test_scores = learning_curve(
            model,
            X,
            Y,
            cv=5,
            scoring="neg_mean_absolute_error",
            train_sizes=np.linspace(0.1, 1.0, 5),
        )

        train_mae = -train_scores
        test_mae = -test_scores

        # Plot the data.
        plt.figure(figsize=(8, 6))
        plt.plot(train_sizes, np.mean(train_mae, axis=1), label="Train MAE")
        plt.plot(train_sizes, np.mean(test_mae, axis=1), label="Val MAE")
        plt.title("Learning Curve (MAE)")
        plt.xlabel("Samples")
        plt.ylabel("MAE")
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()

        # Save the plots if necessary.
        if save:
            os.makedirs(output_dir, exist_ok=True)
            plt.savefig(f"{output_dir}/learning_curve.png")

        plt.show()

    def plot_all(self, save: bool = True, output_dir: str = "plots") -> None:
        """
        Plot all available plots that are defined in this class.
        Plots: `plot_predicted_vs_actual`, `plot_residuals` and `plot_learning_curve`
        passing to each one the arguments that are passed to this function.

        Args:
            save (bool, optional):
                If the generated plots should be saved. Defaults to True.

            output_dir (str, optional):
                Where the generated plots should be saved. Defaults to "plots".
        """
        self.plot_pred_vs_actual(save, output_dir)
        self.plot_residuals(save, output_dir)
        self.plot_learning_curve(save, output_dir)


if __name__ == "__main__":
    random_forest_model = RandomForestBaseline(
        path_to_config="config.yaml",
        path_to_data="data/all_ships_v8_partial.csv",
    )
    random_forest_model.train()
    random_forest_model.evaluate(print_results=True, save_best_model=True)
    random_forest_model.plot_all(save=True)
