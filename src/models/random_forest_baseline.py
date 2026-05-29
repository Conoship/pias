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
from sklearn.metrics import r2_score, mean_absolute_error
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

    # The YAML feature set to use when models/features.yaml is present.
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
        self.r2_scores = []
        self.mae_scores = []
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
        with open("models/model.pkl", "wb") as file:
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
        Print the final results of the training with the average R^2 and the average MAE.
        """
        print(f"Model Performance")
        print(f"Mean R2: {sum(self.r2_scores) / len(self.r2_scores):.4f}")
        print(f"Mean MAE: {sum(self.mae_scores) / len(self.mae_scores):.4f}")

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
                each training fold and the average R^2 and MAE of the model after the training
                is completed. Defaults to `False`.
        """
        if not self.fold_results:
            raise ValueError("No trained models found. Call train() first.")

        self.r2_scores.clear()
        self.mae_scores.clear()
        best_r2 = float("-inf")
        for fold, result in enumerate(self.fold_results):
            # Get data from each fold.
            model = result["model"]
            x_test = result["x_test"]
            y_test = result["y_test"]

            # Make predictions and calculate R^2 and MAE.
            predictions = model.predict(x_test)
            r2 = r2_score(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)

            # Append to the lists.
            self.r2_scores.append(r2)
            self.mae_scores.append(mae)

            # If we want to save the model - check against the best accuracy to save the best performing model.
            if save_best_model and r2 > best_r2:
                self._save_model(model, list(x_test.columns))
                best_r2 = r2
                self.best_fold = fold

            # Print fold results if needed.
            if print_results:
                print(f"Fold {fold + 1}")
                print(f"R2: {r2:.4f}")
                print(f"MAE: {mae:.4f}")

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

    def plot_pred_vs_actual(self, save: bool = True, output_dir: str = "plots") -> None:
        """
        Plot the actual vs the predicted values of the features.

        Args:
            save (bool, optional):
                If the generated plots should be saved. Defaults to True.

            output_dir (str, optional):
                Where the generated plots should be saved. Defaults to "plots".
        """
        # Get the data and calculate R^2 and MAE.
        _, _, y_test, preds = self._get_eval_data()
        r2 = r2_score(y_test, preds)
        mae = mean_absolute_error(y_test, preds)

        # Plot the data.
        plt.figure(figsize=(8, 6))
        plt.scatter(y_test, preds, alpha=0.6)
        plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--")
        plt.text(
            0.05,
            0.9,
            f"$R^2$: {r2:.3f}\nMAE: {mae:.4f}",
            transform=plt.gca().transAxes,
            bbox=dict(facecolor="white", alpha=0.7),
        )
        plt.title("Predicted vs Actual")
        plt.xlabel("Actual")
        plt.ylabel("Predicted")
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
        errors = y_test - preds

        # Plot the data.
        plt.figure(figsize=(8, 6))
        plt.scatter(preds, errors, alpha=0.6)
        plt.axhline(0, color="black")
        plt.title("Residuals")
        plt.xlabel("Predicted")
        plt.ylabel("Error")
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
            scoring="r2",
            train_sizes=np.linspace(0.1, 1.0, 5),
        )

        # Plot the data.
        plt.figure(figsize=(8, 6))
        plt.plot(train_sizes, np.mean(train_scores, axis=1), label="Train $R^2$")
        plt.plot(train_sizes, np.mean(test_scores, axis=1), label="Val $R^2$")
        plt.title("Learning Curve")
        plt.xlabel("Samples")
        plt.ylabel("$R^2$")
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
        path_to_data="data/all_ships_v7.csv",
    )
    random_forest_model.train()
    random_forest_model.evaluate(print_results=True, save_best_model=True)
    random_forest_model.plot_all(save=False)
