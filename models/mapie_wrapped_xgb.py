# Import standard library packages.
from typing import Any

# Import third party packages.
import yaml
import pickle
import pandas as pd
from xgboost import XGBRegressor
from mapie.regression import SplitConformalRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error


class MapieXGBRegressor(object):
    # The name of the target hyperparameter configuration.
    _CONFIG_NAME = "MapieWrappedXGB"

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

    # The number of splits for K-Fold Cross-Validation.
    _K_FOLD_CROSS_SPLITS = 5

    # The confidence level for the MAPIE prediction intervals.
    _CONFIDENCE_LEVEL = 0.95

    # The proportion of training data to use for MAPIE conformalization.
    _CONFORMALIZE_SIZE = 0.2

    def __init__(self, path_to_config: str, path_to_data: str) -> None:
        """
        XGB Regressor Stability Baseline Model with MAPIE conformal prediction intervals.

        Args:
            path_to_config (str):
                The path to the `config.yaml` containing the model hyperparameters.

            path_to_data (str):
                The path to the `.csv` file containing the training data for the model.
        """
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
            df, X, Y (tuple): A tuple containing the Pandas DataFrame, X and Y.
        """
        df = pd.read_csv(self.path_to_data)
        X = df[self._X_FEATURES]
        Y = df[self._Y_LABEL]

        return df, X, Y

    def _load_config(self) -> dict[str, Any]:
        """
        Load the hyperparameters configuration for the specific model.
        """
        with open(self.path_to_config, "r") as f:
            config = yaml.safe_load(f)

        return config[self._CONFIG_NAME]

    def _save_model(self, mapie_model: SplitConformalRegressor) -> None:
        """
        Save the MAPIE-wrapped model as a .pkl binary file, alongside the
        feature columns so inference always uses the correct features.

        Args:
            mapie_model (SplitConformalRegressor):
                The fitted and conformalized MAPIE model to save.
        """
        with open("model.pkl", "wb") as file:
            pickle.dump(
                {"model": mapie_model, "feature_cols": self._X_FEATURES},
                file,
            )

    def _print_results(self) -> None:
        """
        Print the final results of the training with the average R^2 and MAE.
        """
        print("Model Performance")
        print(f"Mean R2:  {sum(self.r2_scores) / len(self.r2_scores):.4f}")
        print(f"Mean MAE: {sum(self.mae_scores) / len(self.mae_scores):.4f}")

    def train(self) -> None:
        df, X, Y = self._load_data()
        groups = df[self._GROUP_BY]

        self.fold_results.clear()

        outer_gkf = GroupKFold(n_splits=self._K_FOLD_CROSS_SPLITS)
        inner_gkf = GroupKFold(n_splits=5)
        xgb_params = self._load_config()

        for train_idx, test_idx in outer_gkf.split(X, Y, groups=groups):
            # Outer fold split.
            x_fold_train = X.iloc[train_idx]
            y_fold_train = Y.iloc[train_idx]
            x_test = X.iloc[test_idx]
            y_test = Y.iloc[test_idx]
            groups_fold = groups.iloc[train_idx]

            # Inner group-aware split into fit + conformalize sets.
            fit_idx, conf_idx = next(
                inner_gkf.split(x_fold_train, y_fold_train, groups=groups_fold)
            )
            x_train = x_fold_train.iloc[fit_idx]
            y_train = y_fold_train.iloc[fit_idx]
            x_conf = x_fold_train.iloc[conf_idx]
            y_conf = y_fold_train.iloc[conf_idx]

            # Build and fit the MAPIE-wrapped XGB model.
            mapie_model = SplitConformalRegressor(
                estimator=XGBRegressor(**xgb_params),
                confidence_level=self._CONFIDENCE_LEVEL,
                prefit=False,
            )
            mapie_model.fit(x_train, y_train)
            mapie_model.conformalize(x_conf, y_conf)

            self.fold_results.append(
                {
                    "model": mapie_model,
                    "x_test": x_test,
                    "y_test": y_test,
                }
            )

    def evaluate(
        self, save_best_model: bool = False, print_results: bool = False
    ) -> None:
        """
        Evaluate all trained fold models, printing predictions and 95% CI widths.

        Raises:
            ValueError:
                If `self.fold_results` is empty and the model has not been trained.

        Args:
            save_best_model (bool, optional):
                Save the best performing fold's MAPIE model as `model.pkl`.
                Defaults to False.

            print_results (bool, optional):
                Print per-fold and aggregate R^2 / MAE results.
                Defaults to False.
        """
        if not self.fold_results:
            raise ValueError("No trained models found. Call train() first.")

        self.r2_scores.clear()
        self.mae_scores.clear()
        best_r2 = float("-inf")

        for fold, result in enumerate(self.fold_results):
            model: SplitConformalRegressor = result["model"]
            x_test: pd.DataFrame = result["x_test"]
            y_test: pd.Series = result["y_test"]

            # MAPIE returns point predictions and a (n_samples, 2) interval array.
            predictions, intervals = model.predict_interval(x_test)
            lower = intervals[:, 0]
            upper = intervals[:, 1]
            avg_ci_width = (upper - lower).mean()

            r2 = r2_score(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)

            self.r2_scores.append(r2)
            self.mae_scores.append(mae)

            if save_best_model and r2 > best_r2:
                self._save_model(model)
                best_r2 = r2

            if print_results:
                print(f"Fold {fold + 1}")
                print(f"  R2:           {r2:.4f}")
                print(f"  MAE:          {mae:.4f}")
                print(
                    f"  Avg CI width: {avg_ci_width:.4f}  "
                    f"({int(self._CONFIDENCE_LEVEL * 100)}% confidence)"
                )

        if print_results:
            self._print_results()


if __name__ == "__main__":
    xgb_model = MapieXGBRegressor(
        path_to_config="config.yaml",
        path_to_data="C:/Users/student01/Desktop/data/all_ships_baseline.csv",
    )
    xgb_model.train()
    xgb_model.evaluate(save_best_model=True, print_results=True)
