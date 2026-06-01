import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_absolute_error

datasets = {
    "all": "data/all_ships_v8.csv",
}


with open("src/models/config.yaml", "r") as f:
    config = yaml.safe_load(f)

xgb_params = config["XGBRegressorLeaveOneOut"]

target = "target_attained_index"
group_col = "ship_id"


feature_groups = {
    "loading_features": [
        "condition_code",
        "trim",
        "mg",
        "vcg",
        "draft_over_depth",
        "displacement_per_length",
    ],
    "v3_geometry_features": [
        "total_compartment_volume",
        "cargo_volume_ratio",
        "fuel_oil_volume_ratio",
        "gas_oil_volume_ratio",
        "potable_water_volume_ratio",
        "ballast_volume_ratio",
        "void_volume_ratio",
        "cargohold_hatch_volume_ratio",
    ],
    "main_dimension_features": [
        "lpp",
        "loa",
        "breadth",
        "depth",
        "slenderness_ratio",
        "breadth_depth_ratio",
        "box_volume",
        "layout_length_lpp_ratio",
    ],
    "compartment_features": [
        "total_compartments",
        "n_subcompartments",
        "subcompartments_per_compartment",
        "avg_permeability",
        "min_permeability",
        "max_permeability",
        "std_permeability",
        "n_pipe_subcompartments",
        "pipe_subcompartment_ratio",
        "compartments_per_meter",
    ],
    "content_features": [
        "n_cargo",
        "n_ballast",
        "n_cargohold_hatch",
        "n_potable_water",
        "n_gas_oil",
        "n_void",
        "n_fuel_oil",
        "n_unknown_content",
        "cargo_ratio",
        "fuel_oil_ratio",
        "gas_oil_ratio",
        "potable_water_ratio",
        "ballast_ratio",
        "void_ratio",
        "cargohold_hatch_ratio",
    ],
    "opening_features": [
        "total_openings",
        "openings_per_compartment",
        "openings_per_meter",
        "mean_opening_length",
        "mean_opening_breadth",
        "mean_opening_height",
        "mean_opening_area",
        "max_opening_area",
        "n_opening_types",
        "n_connected_openings",
    ],
    "spatial_zone_features": [
        "total_layout_length",
        "n_comp_aft",
        "n_comp_mid",
        "n_comp_fwd",
        "n_comp_unknown_zone",
        "avg_perm_aft",
        "avg_perm_mid",
        "avg_perm_fwd",
        "n_void_aft",
        "n_void_mid",
        "n_void_fwd",
        "n_ballast_aft",
        "n_ballast_mid",
        "n_ballast_fwd",
        "n_openings_aft",
        "n_openings_mid",
        "n_openings_fwd",
        "n_openings_unknown_zone",
    ],
}


feature_sets = {
    "loading_only": feature_groups["loading_features"],
    "v3_geometry_only": feature_groups["v3_geometry_features"],
    "loading_plus_v3_geometry": (
        feature_groups["loading_features"] + feature_groups["v3_geometry_features"]
    ),
    "main_dimensions_only": feature_groups["main_dimension_features"],
    "compartments_only": (
        feature_groups["compartment_features"] + feature_groups["content_features"]
    ),
    "openings_only": feature_groups["opening_features"],
    "spatial_zones_only": feature_groups["spatial_zone_features"],
    "geometry_only": (
        feature_groups["main_dimension_features"]
        + feature_groups["spatial_zone_features"]
    ),
    "geometry_plus_compartments": (
        feature_groups["main_dimension_features"]
        + feature_groups["spatial_zone_features"]
        + feature_groups["compartment_features"]
        + feature_groups["content_features"]
        + feature_groups["opening_features"]
    ),
    "all_features": (
        feature_groups["loading_features"]
        + feature_groups["main_dimension_features"]
        + feature_groups["spatial_zone_features"]
        + feature_groups["compartment_features"]
        + feature_groups["content_features"]
        + feature_groups["opening_features"]
    ),
    "all_without_trim_mg": (
        ["draft", "displacement", "vcg"]
        + feature_groups["main_dimension_features"]
        + feature_groups["spatial_zone_features"]
        + feature_groups["compartment_features"]
        + feature_groups["content_features"]
        + feature_groups["opening_features"]
    ),
}


def evaluate_leave_one_ship_out(df, features, target, group_col):
    requested_features = features
    features = [f for f in requested_features if f in df.columns]
    missing_features = [f for f in requested_features if f not in df.columns]

    if missing_features:
        print("Missing features skipped:", missing_features)

    if len(features) == 0:
        raise ValueError("No valid features found in this dataframe.")

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

        mae = mean_absolute_error(y_test, preds)

        if len(y_test) >= 2:
            ship_r2 = r2_score(y_test, preds)
        else:
            ship_r2 = np.nan

        results.append(
            {
                "test_ship": test_ship,
                "n_test_rows": len(y_test),
                "r2": ship_r2,
                "mae": mae,
            }
        )

        all_y_true.extend(y_test.tolist())
        all_y_pred.extend(preds.tolist())

    results_df = pd.DataFrame(results)

    if len(all_y_true) >= 2:
        pooled_r2 = r2_score(all_y_true, all_y_pred)
    else:
        pooled_r2 = np.nan

    pooled_mae = mean_absolute_error(all_y_true, all_y_pred)

    return {
        "features_used": features,
        "mean_r2": pooled_r2,
        "mean_mae": pooled_mae,
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
        print(f"Pooled R2:  {result['mean_r2']:.4f}")
        print(f"Pooled MAE: {result['mean_mae']:.4f}")
        print("\nPer-ship results:")
        print(result["per_ship_results"])


summary_df = pd.DataFrame(summary_rows)
summary_df = summary_df.sort_values(["condition", "mean_r2"], ascending=[True, False])

loading_mae = summary_df[summary_df["feature_set"] == "loading_only"][
    ["condition", "mean_mae"]
].rename(columns={"mean_mae": "loading_only_mae"})
summary_df = summary_df.merge(loading_mae, on="condition", how="left")
summary_df["delta_mae_vs_loading"] = (
    summary_df["mean_mae"] - summary_df["loading_only_mae"]
)

print("\n\nFinal feature-set comparison:")
print(summary_df)

plots_dir = Path("plots/diagnostics")
plots_dir.mkdir(parents=True, exist_ok=True)
summary_df.to_csv(plots_dir / "feature_set_summary.csv", index=False)


plt.figure(figsize=(12, 6))
sns.barplot(data=summary_df, x="feature_set", y="mean_r2", hue="condition")
plt.axhline(0, linestyle="--", color="black")
plt.title("Pooled Leave-One-Ship-Out R2 by Feature Set and Condition")
plt.xlabel("Feature Set")
plt.ylabel("Pooled R2")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(plots_dir / "feature_set_pooled_r2_by_condition.png")
plt.close()

plt.figure(figsize=(12, 6))
sns.barplot(data=summary_df, x="feature_set", y="mean_mae", hue="condition")
plt.title("Pooled Leave-One-Ship-Out MAE by Feature Set and Condition")
plt.xlabel("Feature Set")
plt.ylabel("Pooled MAE")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(plots_dir / "feature_set_pooled_mae_by_condition.png")
plt.close()


print("\nGraphs saved to:")
print(plots_dir)
print("1. feature_set_pooled_r2_by_condition.png")
print("2. feature_set_pooled_mae_by_condition.png")
