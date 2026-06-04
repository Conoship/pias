import pickle
import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.feature_sets import select_feature_columns


DATA_PATH = "data/all_ships_v8.csv"
MODELS_DIR = Path("models")
TARGET = "target_attained_index"
GROUP_COL = "ship_id"
DROP_COLUMNS = [
    "target_margin",
    TARGET,
    "ship_version_id",
    "ship_id",
    "subdivision_length",
]

CONDITIONS = {
    "light": 0,
    "partial": 1,
    "deepest": 2,
}

MODEL_PARAMS = {
    "n_estimators": 300,
    "random_state": 42,
}


def train_one_condition(df, condition_name, condition_code=None):
    print(f"\nTraining {condition_name} model...")

    if condition_code is None:
        condition_df = df.copy()
    else:
        condition_df = df[df["condition_code"] == condition_code].copy()

    if condition_df.empty:
        raise ValueError(f"No rows found for {condition_name}.")

    feature_cols = select_feature_columns(
        condition_df,
        fallback_drop_columns=DROP_COLUMNS,
    )
    X = condition_df[feature_cols].copy()
    y = condition_df[TARGET]
    groups = condition_df[GROUP_COL]

    X = X.fillna(0.0)
    X = X.loc[:, X.nunique(dropna=True) > 1]
    feature_cols = list(X.columns)

    if len(feature_cols) == 0:
        raise ValueError(f"No usable feature columns found for {condition_name}.")

    n_ships = groups.nunique()
    if n_ships < 2:
        raise ValueError(
            f"{condition_name} needs at least 2 ships for validation. "
            f"Found {n_ships}."
        )

    n_splits = min(5, n_ships)
    splitter = GroupKFold(n_splits=n_splits)

    all_y_true = []
    all_y_pred = []

    for train_index, test_index in splitter.split(X, y, groups):
        X_train = X.iloc[train_index]
        y_train = y.iloc[train_index]
        X_test = X.iloc[test_index]
        y_test = y.iloc[test_index]

        model = RandomForestRegressor(**MODEL_PARAMS)
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        all_y_true.extend(y_test.tolist())
        all_y_pred.extend(predictions.tolist())

    mae = mean_absolute_error(all_y_true, all_y_pred)
    r2 = r2_score(all_y_true, all_y_pred) if len(all_y_true) >= 2 else np.nan

    print(f"Rows: {len(condition_df)}")
    print(f"Ships: {n_ships}")
    print(f"Features: {len(feature_cols)}")
    print(f"Validation MAE: {mae:.4f}")
    print(f"Validation R2: {r2:.4f}")

    final_model = RandomForestRegressor(**MODEL_PARAMS)
    final_model.fit(X, y)

    output_path = MODELS_DIR / f"model_{condition_name}.pkl"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as file:
        pickle.dump(
            {
                "model_type": "Random Forest Regressor",
                "model": final_model,
                "feature_cols": feature_cols,
                "engineer_features": None,
            },
            file,
        )

    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        default=DATA_PATH,
        help="One CSV containing all three condition_code values.",
    )
    parser.add_argument("--light", help="CSV already filtered to light condition.")
    parser.add_argument("--partial", help="CSV already filtered to partial condition.")
    parser.add_argument("--deepest", help="CSV already filtered to deepest condition.")
    args = parser.parse_args()

    condition_paths = {
        "light": args.light,
        "partial": args.partial,
        "deepest": args.deepest,
    }

    if all(condition_paths.values()):
        for condition_name, csv_path in condition_paths.items():
            df = pd.read_csv(csv_path)
            train_one_condition(df, condition_name)
    elif any(condition_paths.values()):
        raise ValueError(
            "Pass all three CSVs: --light, --partial, and --deepest."
        )
    else:
        df = pd.read_csv(args.data)
        for condition_name, condition_code in CONDITIONS.items():
            train_one_condition(df, condition_name, condition_code)


if __name__ == "__main__":
    main()
