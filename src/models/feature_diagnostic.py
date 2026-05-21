import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_absolute_error

datasets = {
    "light": "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_light_v5.csv",
    "partial": "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_partial_v5.csv",
    "deepest": "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_deepest_v5.csv",
}


with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

xgb_params = config["XGBRegressorLeaveOneOut"]

target = "target_attained_index"
group_col = "ship_id"

feature_groups = {
    "loading_features": [
        "draft",
        "trim",
        "mg",
        "displacement",
        "vcg",
    ],
    "compartment_features": [
        "openings_per_compartment",
        "total_compartments",
        "avg_permeability",
    ],
    "content_features": [
        "n_cargo",
        "n_ballast",
        "n_cargohold_hatch",
        "n_potable_water",
        "n_gas_oil",
        "n_void",
        "n_fuel_oil",
    ],
    "geometry_features": [
        "total_layout_length",
        "max_layout_breadth",
        "max_layout_height",
        "avg_cross_section",
        "sum_bh_sections",
        "std_breadth",
        "std_height",
        "n_frustum_points",
    ],
}

feature_sets = {
    "loading_only": feature_groups["loading_features"],
    "compartments_only": (
        feature_groups["compartment_features"] + feature_groups["content_features"]
    ),
    "geometry_only": feature_groups["geometry_features"],
    "geometry_plus_compartments": (
        feature_groups["geometry_features"]
        + feature_groups["compartment_features"]
        + feature_groups["content_features"]
    ),
    "all_features": (
        feature_groups["loading_features"]
        + feature_groups["compartment_features"]
        + feature_groups["content_features"]
        + feature_groups["geometry_features"]
    ),
    "all_without_trim_mg": (
        ["draft", "displacement", "vcg", "condition_code"]
        + feature_groups["compartment_features"]
        + feature_groups["content_features"]
        + feature_groups["geometry_features"]
    ),
}


def evaluate_leave_one_ship_out(df, features, target, group_col):
    features = [f for f in features if f in df.columns]

    X = df[features].copy()
    y = df[target]
    ships = df[group_col].unique()

    results = []

    all_y_true = []
    all_y_pred = []

    for test_ship in ships:
        train_mask = df[group_col] != test_ship
        test_mask = df[group_col] == test_ship

        X_train = X[train_mask]
        y_train = y[train_mask]

        X_test = X[test_mask]
        y_test = y[test_mask]

        model = XGBRegressor(**xgb_params)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)

        r2 = r2_score(y_test, preds)
        mae = mean_absolute_error(y_test, preds)

        results.append(
            {
                "test_ship": test_ship,
                "r2": r2,
                "mae": mae,
            }
        )

        all_y_true.extend(y_test.tolist())
        all_y_pred.extend(preds.tolist())

    results_df = pd.DataFrame(results)

    return {
        "features_used": features,
        "mean_r2": results_df["r2"].mean(),
        "mean_mae": results_df["mae"].mean(),
        "per_ship_results": results_df,
    }


summary_rows = []

for condition_name, csv_path in datasets.items():
    df = pd.read_csv(csv_path)

    for set_name, features in feature_sets.items():
        result = evaluate_leave_one_ship_out(
            df=df,
            features=features,
            target=target,
            group_col=group_col,
        )

        summary_rows.append(
            {
                "condition": condition_name,
                "feature_set": set_name,
                "n_features": len(result["features_used"]),
                "mean_r2": result["mean_r2"],
                "mean_mae": result["mean_mae"],
            }
        )

        print("\n==============================")
        print(f"Condition: {condition_name}")
        print(f"Feature set: {set_name}")
        print(f"Features used: {result['features_used']}")
        print(f"Mean R2:  {result['mean_r2']:.4f}")
        print(f"Mean MAE: {result['mean_mae']:.4f}")
        print("\nPer-ship results:")
        print(result["per_ship_results"])


summary_df = pd.DataFrame(summary_rows)
summary_df = summary_df.sort_values(["condition", "mean_r2"], ascending=[True, False])

print("\n\nFinal feature-set comparison:")
print(summary_df)

plots_dir = Path("C:/Users/student01/Desktop/rug-project/pias/plots/diagnostics")
plots_dir.mkdir(parents=True, exist_ok=True)


# Graph 1: Mean R2 by feature set and condition
plt.figure(figsize=(12, 6))
sns.barplot(data=summary_df, x="feature_set", y="mean_r2", hue="condition")
plt.axhline(0, linestyle="--", color="black")
plt.title("Mean R2 by Feature Set and Condition")
plt.xlabel("Feature Set")
plt.ylabel("Mean R2")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(plots_dir / "feature_set_mean_r2_by_condition.png")
plt.close()


# Graph 2: Mean MAE by feature set and condition
plt.figure(figsize=(12, 6))
sns.barplot(data=summary_df, x="feature_set", y="mean_mae", hue="condition")
plt.title("Mean MAE by Feature Set and Condition")
plt.xlabel("Feature Set")
plt.ylabel("Mean MAE")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(plots_dir / "feature_set_mean_mae_by_condition.png")
plt.close()


print("\nGraphs saved to:")
print(plots_dir)
print("1. feature_set_mean_r2_by_condition.png")
print("2. feature_set_mean_mae_by_condition.png")
