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

    def __init__(self, path_to_config, path_to_data):
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

    def _load_config(self):
        """
        Load the hyperparameters configuration for the specific model.
        This method uses the constructor argument `path_to_config`.
        """
        config = {}
        with open(self.path_to_config, "r") as f:
            config = yaml.safe_load(f)

        return config[self._CONFIG_NAME]

    def _save_model(self, model: XGBRegressor):
        """
        Save the model as a .pkl binary file.

        Args:
            model (XGBRegressor):
                The XGB Regressor model to save as the .pkl file.
        """
        with open("model.pkl", "wb") as file:
            pickle.dump(model, file)

    def _print_results(self):
        """
        Print the final results of the training with the average R^2 and the average MAE.
        """
        print(f"Model Performance")
        print(f"Mean R2: {sum(self.r2_scores) / len(self.r2_scores):.4f}")
        print(f"Mean MAE: {sum(self.mae_scores) / len(self.mae_scores):.4f}")

    # Train and evaluate the model.
    def train_and_evaluate_model(
        self, save_best_model: bool = False, print_training_results: bool = False
    ):
        """
        Train the model and perform K-Fold Cross-Validation in parallel.

        Args:
            save_best_model (bool):
                Boolean flag to enable the user to save the best performing model
                by comparing in each fold the accuracy to the previous fold accuracy.
                Defaults to `False`.

            print_training_results (bool):
                Boolean flag to enable logging and print to the console the results of
                each training fold and the average R^2 and MAE of the model after the training
                is completed. Defaults to `False`.
        """
        # Load Data.
        df = pd.read_csv(self.path_to_data)

        # Define Features (X) and Target (Y).
        X = df[self._X_FEATURES]
        Y = df[self._Y_LABEL]
        groups = df[self._GROUP_BY]

        # K-Fold Cross-validation.
        gkf = GroupKFold(n_splits=self._K_FOLD_CROSS_SPLITS)
        xgb_params = self._load_config()
        previous_r2 = 0
        for fold, (train_idx, test_idx) in enumerate(gkf.split(X, Y, groups=groups)):
            x_train, x_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = Y.iloc[train_idx], Y.iloc[test_idx]

            # Train the model.
            model = XGBRegressor(**xgb_params)
            model.fit(x_train, y_train, eval_set=[(x_test, y_test)], verbose=False)

            # Evaluate Performance.
            predictions = model.predict(x_test)
            r2 = r2_score(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)

            # Save the model if it performed better than the last fold version.
            if save_best_model and r2 > previous_r2:
                self._save_model(model)

            # Append to the corresponding list and update last R2 variable.
            self.r2_scores.append(r2)
            self.mae_scores.append(mae)
            previous_r2 = r2

            # Print fold results.
            if print_training_results:
                print(f"Fold {fold + 1}")
                print(f"R2: {predictions}")
                print(f"MAE: {mae}")

        if print_training_results:
            self._print_results()


if __name__ == "__main__":
    xgb_model = XGBStabilityBaseline(
        path_to_config="config.yaml",
        path_to_data="C:/Users/student02/data/all_ships_all_conditions_v4.csv",
    )
    xgb_model.train_and_evaluate_model(print_training_results=True)
