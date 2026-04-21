import joblib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Load the data
df = pd.read_csv("C:/Users/student02/data/all_loads_all_features.csv")

CONDITIONS = {0: "light", 1: "partial", 2: "deepest"}

# 1. How many rows per ship version? (should be 3)
print("Total rows:", len(df))
print("\nRows per ship version (first 10):")
print(df["ship_version_id"].value_counts().head(10))

# 2. Target distribution
print("\nTarget stats:")
print(df["target_attained_index"].describe())

# 3. How much does the target vary within each ship version?
print("\nTarget variance by ship_version_id:")
print(df.groupby("ship_version_id")["target_attained_index"].std().describe())

# 4. Correlation of each feature with the target
features = [
    "openings_per_compartment",
    "total_compartments",
    "avg_permeability",
    "n_cargo",
    "n_ballast",
    "n_cargohold_hatch",
    "n_potable_water",
    "n_gas_oil",
    "n_void",
    "n_fuel_oil",
    "total_layout_length",
    "max_layout_breadth",
    "max_layout_height",
    "avg_cross_section",
    "sum_bh_sections",
    "std_breadth",
    "std_height",
    "n_frustum_points",
]
features = [f for f in features if f in df.columns]

correlations = (
    df[features + ["target_attained_index"]]
    .corr()["target_attained_index"]
    .drop("target_attained_index")
)
correlations = correlations.abs().sort_values(ascending=False)

print(
    df.groupby("ship_version_id")["target_attained_index"].agg(["min", "max", "mean"])
)

print("\nCorrelation of each feature with target:")
print(correlations)

# 5. Plot the correlations
plt.figure(figsize=(10, 6))
sns.barplot(x=correlations.values, y=correlations.index, palette="viridis")
plt.title("How strongly does feature relate to the target?")
plt.xlabel("Correlation (0 = no relation, 1 = perfect relation)")
plt.tight_layout()
plt.savefig("C:/Users/student02/data/plots/feature_correlations.png")
plt.close()
print("\nPlot saved!")

# 6. Within-ship vs between-ship variance
print("\nTarget stats per ship:")
print(df.groupby("ship_id")["target_attained_index"].agg(["min", "max", "mean", "std"]))

# 7. Feature importance per condition
for code, name in CONDITIONS.items():
    model_path = f"models/xgb_{name}.joblib"
    if not Path(model_path).exists():
        print(f"No model found for {name}, skipping.")
        continue
    model = joblib.load(model_path)
    importances = pd.Series(model.feature_importances_, index=model.feature_names_in_)
    print(f"\n{name.upper()} feature importances:")
    print(importances.sort_values(ascending=False))

# 8. MAE per ship per condition
for code, name in CONDITIONS.items():
    model_path = f"models/xgb_{name}.joblib"
    if not Path(model_path).exists():
        print(f"No model found for {name}, skipping.")
        continue
    model = joblib.load(model_path)
    subset = df[df["condition_code"] == code].copy()
    X = subset[list(model.feature_names_in_)]
    subset["error"] = (subset["target_attained_index"] - model.predict(X)).abs()
    print(f"\n{name.upper()} MAE per ship:")
    print(subset.groupby("ship_id")["error"].mean())