# Import standard library packages.
from typing import Any

# Import third party packages.
import yaml
import pickle
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error


class XGBStabilityBaseline(object):
    # The name of the target hyperparameter configuration.
    _CONFIG_NAME = "XGBRegressorBaseline"

    # The columns of the dataset to use as features (X).
    _X_FEATURES = [
        "draft",
        "vcg",
        "displacement",
        "condition_code",
        "trim",
        "openings_per_compartment",
        "total_compartments",
    ]

    # The column of the dataset to use as label (Y).
    _Y_LABEL = "target_margin"

    # The column by which we create the groups for K-Fold Cross-Validation.
    _GROUP_BY = "ship_version_id"

    # The number of splits for K-Fold Cross-Validation
    _K_FOLD_CROSS_SPLITS = 5

    def __init__(self, path_to_config: str, path_to_data: str) -> None:
        """
        XGB Regressor Stablity Baseline Model.

        Args:
            path_to_config (str):
                The path to the `config.yaml` containing the model hyperparameters.

            path_to_data (str):
                The path to the `.csv` file containing the training data for the model.
        """
        # Get constructor argument.
        self.path_to_config = path_to_config
        self.path_to_data = path_to_data

        # Lists to hold results.
        self.r2_scores = []
        self.mae_scores = []
        self.fold_results = []

    def _load_data(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        """
        Load the data from the CSV into a Pandas DataFrame and get X and Y.

        Returns:
            df, X, Y (tuple): A tuple containing the Pandas DataFrame, X and Y
        """
        df = pd.read_csv(self.path_to_data)
        X = df[self._X_FEATURES]
        Y = df[self._Y_LABEL]

        return df, X, Y

    def _load_config(self) -> dict[str, Any]:
        """
        Load the hyperparameters configuration for the specific model.
        This method uses the constructor argument `path_to_config`.
        """
        config = {}
        with open(self.path_to_config, "r") as f:
            config = yaml.safe_load(f)

        return config[self._CONFIG_NAME]

    def _save_model(self, model: XGBRegressor) -> None:
        """
        Save the model as a .pkl binary file.

        Args:
            model (XGBRegressor):
                The XGB Regressor model to save as the .pkl file.
        """
        with open("model.pkl", "wb") as file:
            pickle.dump({"model": model, "feature_cols": self._X_FEATURES}, file)

    def _print_results(self) -> None:
        """
        Print the final results of the training with the average R^2 and the average MAE.
        """
        print(f"Model Performance")
        print(f"Mean R2: {sum(self.r2_scores) / len(self.r2_scores):.4f}")
        print(f"Mean MAE: {sum(self.mae_scores) / len(self.mae_scores):.4f}")

    def train(self) -> None:
        """
        Train models for each fold and store them internally.
        """
        # Load Data.
        df, X, Y = self._load_data()
        groups = df[self._GROUP_BY]

        # Clear previous results.
        self.fold_results.clear()

        # Cross-validation.
        gkf = GroupKFold(n_splits=self._K_FOLD_CROSS_SPLITS)
        xgb_params = self._load_config()
        for train_idx, test_idx in gkf.split(X, Y, groups=groups):
            # Train Data.
            x_train = X.iloc[train_idx]
            y_train = Y.iloc[train_idx]

            # Test Data.
            x_test = X.iloc[test_idx]
            y_test = Y.iloc[test_idx]

            # Train model.
            model = XGBRegressor(**xgb_params)
            model.fit(
                x_train,
                y_train,
                eval_set=[(x_test, y_test)],
                verbose=False,
            )

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
                self._save_model(model)
                best_r2 = r2

            # Print fold results if needed.
            if print_results:
                print(f"Fold {fold + 1}")
                print(f"R2: {r2:.4f}")
                print(f"MAE: {mae:.4f}")

        if print_results:
            self._print_results()


if __name__ == "__main__":
    xgb_model = XGBStabilityBaseline(
        path_to_config="config.yaml",
        path_to_data="C:/Users/student01/Desktop/data/all_ships_baseline.csv",
    )
    xgb_model.train()
    xgb_model.evaluate(print_results=True, save_best_model=True)
