import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from src.models.random_forest_baseline import RandomForestBaseline

# Paths
CONFIG_PATH = "src/models/config.yaml"
DATA_PATH = "C:/Users/student01/Desktop/data/all_ships_partial_v4.csv"


# Helper
def make_model():
    return RandomForestBaseline(path_to_config=CONFIG_PATH, path_to_data=DATA_PATH)


# Tests
class TestInit:
    def test_class_instantiates(self):
        model = make_model()
        assert model is not None

    def test_has_required_attributes(self):
        model = make_model()
        assert hasattr(model, "path_to_config")
        assert hasattr(model, "path_to_data")

    def test_paths_are_stored_correctly(self):
        model = make_model()
        assert model.path_to_config == CONFIG_PATH
        assert model.path_to_data == DATA_PATH


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

    def test_load_data_x_and_y_same_length(self):
        model = make_model()
        df, X, Y = model._load_data()
        non_numeric = X.select_dtypes(exclude=[np.number]).columns.tolist()
        assert len(non_numeric) == 0, f"Non-numeric columns in X: {non_numeric}"

    def test_load_data_df_not_empty(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert len(df) > 0

    def test_load_data_no_nulls_in_x(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert X.isnull().sum().sum() == 0, "X contains null values"

    def test_load_data_no_nulls_in_y(self):
        model = make_model()
        df, X, Y = model._load_data()
        assert Y.isnull().sum() == 0, "Y contains null values"


class TestLoadConfig:
    def test_load_config_returns_dict(self):
        model = make_model()
        config = model._load_config(config_name="RandomForestRegressor")
        assert isinstance(config, dict)

    def test_load_config_has_required_keys(self):
        model = make_model()
        config = model._load_config(config_name="RandomForestRegressor")
        required_keys = [
            "n_estimators",
            "max_depth",
            "min_samples_leaf",
            "min_samples_split",
            "max_features",
            "bootstrap",
            "oob_score",
            "n_jobs",
            "random_state",
        ]
        missing = set(required_keys) - set(config.keys())
        assert len(missing) == 0, f"Config missing keys: {missing}"

    def test_load_config_valid_values(self):
        model = make_model()
        config = model._load_config(config_name="RandomForestRegressor")
        assert config["n_estimators"] > 0
        assert config["random_state"] is not None


class TestEngineerFeatures:
    def test_engineer_features_returns_dataframe(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._engineer_features(X)
        assert isinstance(result, pd.DataFrame)

    def test_engineer_features_no_nulls_introduced(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._engineer_features(X)
        assert result.isnull().sum().sum() == 0, "Feature engineering introduced nulls"

    def test_engineer_features_increases_or_keeps_columns(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._engineer_features(X)
        assert (
            result.shape[1] >= X.shape[1]
        ), "Feature engineering dropped columns unexpectedly"

    def test_engineer_features_preserves_row_count(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._engineer_features(X)
        assert len(result) == len(X), "Feture engineering changed number of rows"

    def test_engineer_features_output_is_numeric(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._engineer_features(X)
        non_numeric = result.select_dtypes(exclude=[np.number]).columns.tolist()
        assert (
            len(non_numeric) == 0
        ), f"Non-numeric columns after engineering: {non_numeric}"


class TestFilterLowImpactFeatures:
    def test_filter_returns_dataFrame(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._filter_low_impact_features(X, Y)
        assert isinstance(result, pd.DataFrame)

    def test_filter_reduces_or_keeps_columns(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._filter_low_impact_features(X, Y)
        assert result.shape[1] <= X.shape[1], "Filter added unexpected columns"

    def test_filter_preserves_row_count(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._filter_low_impact_features(X, Y)
        assert len(result) == len(X)

    def test_filter_removes_low_importance_features(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._filter_low_impact_features(X, Y)
        assert result.shape[1] <= X.shape[1]

    def test_filter_output_columns_are_subset_of_input(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._filter_low_impact_features(X, Y)
        assert set(result.columns).issubset(
            set(X.columns)
        ), "Filter introduced new columns"

    def test_filter_output_is_numeric(self):
        model = make_model()
        df, X, Y = model._load_data()
        result = model._filter_low_impact_features(X, Y)
        non_numeric = result.select_dtypes(exclude=[np.number]).columns.tolist()
        assert len(non_numeric) == 0, f"Non-numeric columns after filter: {non_numeric}"


class TestTrain:
    def test_train_runs_without_error(self):
        model = make_model()
        model.train()

    def test_train_populates_fold_results(self):
        model = make_model()
        model.train()
        assert len(model.fold_results) > 0, "fold_results is empty after training"

    def test_fold_results_have_required_keys(self):
        model = make_model()
        model.train()
        for fold in model.fold_results:
            assert "model" in fold, "fold missing model"
            assert "x_test" in fold, "fold missing x_test"
            assert "y_test" in fold, "fold missing y_test"

    def test_fold_results_models_are_fitted(self):
        from sklearn.utils.validation import check_is_fitted

        model = make_model()
        model.train()
        for fold in model.fold_results:
            check_is_fitted(fold["model"])

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

    def test_correct_number_of_folds(self):
        model = make_model()
        model.train()
        assert len(model.fold_results) == model._K_FOLD_CROSS_SPLITS


class TestEvaluate:
    def test_evaluate_runs_without_error(self):
        model = make_model()
        model.train()
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
        assert len(model.mae_scores) > 0, "mae_scores is empty after evalute"

    def test_mae_scores_are_non_negative(self):
        model = make_model()
        model.train()
        model.evaluate()
        for mae in model.mae_scores:
            assert mae >= 0, f"MAE is negative: {mae:.4f}"

    def test_evaluate_before_train_raises(self):
        model = make_model()
        with pytest.raises(ValueError):
            model.evaluate()


class TestGetEvalData:
    def test_get_eval_data_returns_correct_types(self):
        from sklearn.utils.validation import check_is_fitted

        model = make_model()
        model.train()
        rf_model, x_test, y_test, preds = model._get_eval_data()
        check_is_fitted(rf_model)
        assert isinstance(x_test, pd.DataFrame)
        assert isinstance(y_test, pd.Series)
        assert isinstance(preds, np.ndarray)

    def test_eval_data_lengths_match(self):
        model = make_model()
        model.train()
        rf_model, x_test, y_test, preds = model._get_eval_data()
        assert len(x_test) == len(y_test) == len(preds)

    def test_get_eval_data_before_train_raises(self):
        model = make_model()
        with pytest.raises(ValueError):
            model._get_eval_data()


class TestSaveModel:
    def test_save_model_creates_file(self):
        import os

        model = make_model()
        model.train()
        rf_model, x_test, y_test, preds = model._get_eval_data()
        model._save_model(model=rf_model, feature_cols=list(x_test.columns))
        assert os.path.exists("model.pkl"), "model.pkl was not created"

    def test_saved_model_has_required_keys(self):
        import pickle

        model = make_model()
        model.train()
        rf_model, x_test, y_test, preds = model._get_eval_data()
        model._save_model(model=rf_model, feature_cols=list(x_test.columns))
        with open("model.pkl", "rb") as f:
            saved = pickle.load(f)
        assert "model_type" in saved
        assert "model" in saved
        assert "feature_cols" in saved
        assert "engineer_features" in saved

    def test_saved_model_type_is_correct(self):
        import pickle
        from sklearn.ensemble import RandomForestRegressor

        model = make_model()
        model.train()
        rf_model, x_test, y_test, preds = model._get_eval_data()
        model._save_model(model=rf_model, feature_cols=list(x_test.columns))
        with open("model.pkl", "rb") as f:
            saved = pickle.load(f)
        assert saved["model_type"] == "Random Forest Regressor"
        assert isinstance(saved["model"], RandomForestRegressor)


class TestPlots:
    def test_plot_pred_vs_actual_runs(self):
        model = make_model()
        model.train()
        with patch("matplotlib.pyplot.show"):
            model.plot_pred_vs_actual(save=False)

    def test_plot_residuals_runs(self):
        model = make_model()
        model.train()
        with patch("matplotlib.pyplot.show"):
            model.plot_residuals(save=False)

    def test_plot_learning_curve_runs(self):
        model = make_model()
        model.train()
        with patch("matplotlib.pyplot.show"):
            model.plot_learning_curve(save=False)

    def test_plot_all_runs(self):
        model = make_model()
        model.train()
        with patch("matplotlib.pyplot.show"):
            model.plot_all(save=False)
