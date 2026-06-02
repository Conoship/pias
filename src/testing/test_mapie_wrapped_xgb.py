# Import standard library packages.
import os
import pickle

# Import third party packages.
import numpy as np
import pandas as pd
import pytest
from mapie.regression import SplitConformalRegressor

# Import local packages.
from src.models.mapie_wrapped_xgb import MapieXGBRegressor

CONFIG_PATH = "C:/Users/student01/Desktop/rug-project/pias/config.yaml"
DATA_PATH = "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_v8.csv"


def make_model() -> MapieXGBRegressor:
    return MapieXGBRegressor(path_to_config=CONFIG_PATH, path_to_data=DATA_PATH)


class TestInit:
    def test_class_instantiates(self):
        model = make_model()
        assert model is not None

    def test_has_path_to_config(self):
        model = make_model()
        assert hasattr(model, "path_to_config")

    def test_has_path_to_data(self):
        model = make_model()
        assert hasattr(model, "path_to_data")

    def test_path_to_config_stored_correctly(self):
        model = make_model()
        assert model.path_to_config == CONFIG_PATH

    def test_path_to_data_stored_correctly(self):
        model = make_model()
        assert model.path_to_data == DATA_PATH

    def test_r2_scores_starts_empty(self):
        model = make_model()
        assert model.r2_scores == []

    def test_mae_scores_starts_empty(self):
        model = make_model()
        assert model.mae_scores == []

    def test_fold_results_starts_empty(self):
        model = make_model()
        assert model.fold_results == []


class TestLoadData:
    def test_load_data_returns_tuple(self):
        model = make_model()
        result = model._load_data()
        assert isinstance(result, tuple)

    def test_load_data_returns_three_elements(self):
        model = make_model()
        result = model._load_data()
        assert len(result) == 3

    def test_load_data_df_is_dataframe(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert isinstance(df, pd.DataFrame)

    def test_load_data_x_is_dataframe(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert isinstance(X, pd.DataFrame)

    def test_load_data_y_is_series(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert isinstance(Y, pd.Series)

    def test_load_data_y_has_correct_name(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert Y.name == MapieXGBRegressor._Y_LABEL

    def test_load_data_df_not_empty(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert len(df) > 0

    def test_load_data_x_and_y_same_length(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert len(X) == len(Y)

    def test_load_data_x_is_all_numeric(self):
        model = make_model()
        df, X, Y = model._load_data()
        non_numeric = X.select_dtypes(exclude=[np.number]).columns.tolist()
        assert len(non_numeric) == 0, f"Non-numeric columns in X: {non_numeric}"

    def test_load_data_no_nulls_in_y(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert Y.isnull().sum() == 0, "Y contains null values"


class TestLoadConfig:
    def test_load_config_returns_dict(self):
        model = make_model()
        config = model._load_config()
        assert isinstance(config, dict)

    def test_load_config_has_n_estimators(self):
        model = make_model()
        config = model._load_config()
        assert "n_estimators" in config

    def test_load_config_n_estimators_positive(self):
        model = make_model()
        config = model._load_config()
        assert config["n_estimators"] > 0

    def test_load_config_has_random_state(self):
        model = make_model()
        config = model._load_config()
        assert "random_state" in config

    def test_load_config_missing_key_raises(self):
        model = MapieXGBRegressor(path_to_config="", path_to_data=DATA_PATH)
        with pytest.raises((KeyError, FileNotFoundError)):
            model._load_config()


class TestTrain:
    def test_train_runs_without_error(self):
        model = make_model()
        model.train()

    def test_train_populates_fold_results(self):
        model = make_model()
        model.train()
        assert len(model.fold_results) > 0, "fold_results is empty after training"

    def test_train_correct_number_of_folds(self):
        model = make_model()
        model.train()
        assert len(model.fold_results) == model._K_FOLD_CROSS_SPLITS

    def test_fold_results_have_model_key(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert "model" in fold

    def test_fold_results_have_x_test_key(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert "x_test" in fold

    def test_fold_results_have_y_test_key(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert "y_test" in fold

    def test_fold_results_model_is_mapie(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert isinstance(fold["model"], SplitConformalRegressor)

    def test_fold_results_x_test_is_dataframe(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert isinstance(fold["x_test"], pd.DataFrame)

    def test_fold_results_y_test_is_series(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert isinstance(fold["y_test"], pd.Series)

    def test_fold_results_x_and_y_same_length(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert len(fold["x_test"]) == len(fold["y_test"])

    def test_train_clears_previous_fold_results(self):
        model = make_model()
        model.train()
        first_run = len(model.fold_results)
        model.train()
        second_run = len(model.fold_results)
        assert first_run == second_run, "fold_results not cleared between runs"


class TestEvaluate:
    def test_evaluate_runs_without_error(self):
        model = make_model()
        model.train()
        model.evaluate()

    def test_evaluate_before_train_raises(self):
        model = make_model()
        with pytest.raises(ValueError):
            model.evaluate()

    def test_evaluate_populates_r2_scores(self):
        model = make_model()
        model.train()
        model.evaluate()
        assert len(model.r2_scores) > 0, "r2_scores is empty after evaluate"

    def test_evaluate_populates_mae_scores(self):
        model = make_model()
        model.train()
        model.evaluate()
        assert len(model.mae_scores) > 0, "mae_scores is empty after evaluate"

    def test_evaluate_correct_number_of_r2_scores(self):
        model = make_model()
        model.train()
        model.evaluate()
        assert len(model.r2_scores) == model._K_FOLD_CROSS_SPLITS

    def test_evaluate_correct_number_of_mae_scores(self):
        model = make_model()
        model.train()
        model.evaluate()
        assert len(model.mae_scores) == model._K_FOLD_CROSS_SPLITS

    def test_mae_scores_are_non_negative(self):
        model = make_model()
        model.train()
        model.evaluate()
        for mae in model.mae_scores:
            assert mae >= 0, f"MAE is negative: {mae:.4f}"

    def test_r2_scores_are_floats(self):
        model = make_model()
        model.train()
        model.evaluate()
        for r2 in model.r2_scores:
            assert isinstance(r2, float)

    def test_evaluate_does_not_accumulate_scores_on_second_call(self):
        model = make_model()
        model.train()
        model.evaluate()
        model.evaluate()
        assert len(model.r2_scores) == model._K_FOLD_CROSS_SPLITS

    def test_evaluate_print_results_contains_r2(self, capsys):
        model = make_model()
        model.train()
        model.evaluate(print_results=True)
        assert "R2" in capsys.readouterr().out

    def test_evaluate_print_results_contains_mae(self, capsys):
        model = make_model()
        model.train()
        model.evaluate(print_results=True)
        assert "MAE" in capsys.readouterr().out


class TestSaveModel:
    def test_save_model_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        assert os.path.exists("model_deepest.pkl"), "model_deepest.pkl was not created"

    def test_saved_model_has_model_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)
        assert "model" in saved

    def test_saved_model_has_model_type_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)
        assert "model_type" in saved

    def test_saved_model_has_feature_cols_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)
        assert "feature_cols" in saved

    def test_saved_model_has_engineer_features_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)
        assert "engineer_features" in saved

    def test_saved_model_type_is_correct(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)
        assert saved["model_type"] == "MAPIE XGB Regressor"

    def test_saved_model_is_mapie(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model = make_model()
        model.train()
        model.evaluate(save_best_model=True)
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)
        assert isinstance(saved["model"], SplitConformalRegressor)


class TestFullPipeline:
    def test_train_evaluate_save_load(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        # Train
        model = make_model()
        model.train()

        # Evaluate and Save
        model.evaluate(save_best_model=True, print_results=False)

        # Load the saved model
        with open("model_deepest.pkl", "rb") as f:
            saved = pickle.load(f)

        # Run inference with the loaded model
        df, X, _ = model._load_data()
        sample = X.iloc[:5]
        predictions, intervals = saved["model"].predict_interval(sample)

        # Assert the predictions
        assert len(predictions) == 5
        assert intervals.shape == (5, 2, 1)
        assert all(
            intervals[:, 0, 0] < intervals[:, 1, 0]
        ), "Lower bound exceeds upper bound"
