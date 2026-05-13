import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances

# Load the data
df = pd.read_csv("C:/Users/student02/data/all_loads_all_features.csv")

CONDITIONS = {0: "light", 1: "partial", 2: "deepest"}

# Make sure plot folder exists
Path("C:/Users/student02/data/plots").mkdir(parents=True, exist_ok=True)

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
    .corr(numeric_only=True)["target_attained_index"]
    .drop("target_attained_index")
)

correlations = correlations.abs().sort_values(ascending=False)

print("\nTarget min/max/mean per ship version:")
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

# 7. Target by condition
if "condition_code" in df.columns:
    df["condition_name"] = df["condition_code"].map(CONDITIONS)

    print("\nTarget stats per condition:")
    print(
        df.groupby("condition_name")["target_attained_index"].agg(
            ["count", "min", "max", "mean", "std"]
        )
    )

    print("\nTarget stats per ship and condition:")
    print(
        df.groupby(["ship_id", "condition_name"])["target_attained_index"].agg(
            ["min", "max", "mean", "std"]
        )
    )

GOOD_SHIPS = [2, 3, 5, 7]
BAD_SHIPS = [1, 4, 6]

df["prediction_group"] = np.where(
    df["ship_id"].isin(GOOD_SHIPS),
    "good_predicted",
    "bad_predicted"
)

similarity_features = [
    "draft",
    "trim",
    "mg",
    "displacement",
    "vcg",
    "condition_code",

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

similarity_features = [f for f in similarity_features if f in df.columns]

print("\nSimilarity features used:")
print(similarity_features)

ship_df = (
    df.groupby("ship_id")[similarity_features + ["target_attained_index"]]
    .agg(["mean", "std", "min", "max"])
)

ship_df.columns = [
    f"{col}_{stat}" for col, stat in ship_df.columns
]

ship_df = ship_df.reset_index()

ship_df["prediction_group"] = np.where(
    ship_df["ship_id"].isin(GOOD_SHIPS),
    "good_predicted",
    "bad_predicted"
)

print("\nShip-level summary:")
print(ship_df)

ship_df.to_csv(
    "C:/Users/student02/data/plots/ship_level_summary.csv",
    index=False
)


numeric_cols = ship_df.select_dtypes(include=["number"]).columns.tolist()
numeric_cols = [c for c in numeric_cols if c != "ship_id"]

good_df = ship_df[ship_df["prediction_group"] == "good_predicted"]
bad_df = ship_df[ship_df["prediction_group"] == "bad_predicted"]

comparison_rows = []

for col in numeric_cols:
    good_mean = good_df[col].mean()
    bad_mean = bad_df[col].mean()
    overall_std = ship_df[col].std()

    if overall_std == 0 or pd.isna(overall_std):
        continue

    effect_size = abs(good_mean - bad_mean) / overall_std

    comparison_rows.append({
        "feature": col,
        "good_mean": good_mean,
        "bad_mean": bad_mean,
        "difference": good_mean - bad_mean,
        "abs_difference": abs(good_mean - bad_mean),
        "effect_size": effect_size,
    })

comparison_df = pd.DataFrame(comparison_rows)
comparison_df = comparison_df.sort_values("effect_size", ascending=False)

print("\nTop features separating good-predicted and bad-predicted ships:")
print(comparison_df.head(20))

comparison_df.to_csv(
    "C:/Users/student02/data/plots/good_vs_bad_feature_differences.csv",
    index=False
)

plt.figure(figsize=(10, 7))
sns.barplot(
    data=comparison_df.head(15),
    x="effect_size",
    y="feature",
    palette="viridis"
)
plt.title("Features Separating Good-Predicted vs Bad-Predicted Ships")
plt.xlabel("Effect size: |good mean - bad mean| / overall std")
plt.ylabel("Feature")
plt.tight_layout()
plt.savefig("C:/Users/student02/data/plots/good_vs_bad_feature_differences.png")
plt.close()


top_features = comparison_df.head(15)["feature"].tolist()

heatmap_data = ship_df[["ship_id"] + top_features].copy()
heatmap_data = heatmap_data.set_index("ship_id")

heatmap_data = heatmap_data.replace([np.inf, -np.inf], np.nan)
heatmap_data = heatmap_data.fillna(heatmap_data.median())

scaler = StandardScaler()
heatmap_scaled = scaler.fit_transform(heatmap_data)

heatmap_scaled_df = pd.DataFrame(
    heatmap_scaled,
    index=heatmap_data.index,
    columns=heatmap_data.columns
)

plt.figure(figsize=(14, 6))
sns.heatmap(
    heatmap_scaled_df,
    annot=True,
    cmap="coolwarm",
    center=0,
    fmt=".2f"
)
plt.title("Standardized Ship Profiles for Most Separating Features")
plt.xlabel("Feature")
plt.ylabel("Ship ID")
plt.tight_layout()
plt.savefig("C:/Users/student02/data/plots/ship_profile_heatmap.png")
plt.close()

X_ship = ship_df[numeric_cols].copy()
X_ship = X_ship.replace([np.inf, -np.inf], np.nan)
X_ship = X_ship.fillna(X_ship.median())

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_ship)

pca = PCA(n_components=2)
pca_coords = pca.fit_transform(X_scaled)

pca_df = pd.DataFrame({
    "ship_id": ship_df["ship_id"],
    "PC1": pca_coords[:, 0],
    "PC2": pca_coords[:, 1],
    "prediction_group": ship_df["prediction_group"],
})

print("\nPCA explained variance:")
print(f"PC1: {pca.explained_variance_ratio_[0]:.3f}")
print(f"PC2: {pca.explained_variance_ratio_[1]:.3f}")
print(f"Total: {pca.explained_variance_ratio_[:2].sum():.3f}")

plt.figure(figsize=(8, 6))
sns.scatterplot(
    data=pca_df,
    x="PC1",
    y="PC2",
    hue="prediction_group",
    s=130
)

for _, row in pca_df.iterrows():
    plt.text(
        row["PC1"] + 0.03,
        row["PC2"] + 0.03,
        str(int(row["ship_id"])),
        fontsize=11
    )

plt.title("Ship Similarity Map using PCA")
plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)")
plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)")
plt.tight_layout()
plt.savefig("C:/Users/student02/data/plots/ship_similarity_pca.png")
plt.close()

pca_df.to_csv(
    "C:/Users/student02/data/plots/ship_similarity_pca.csv",
    index=False
)

dist_matrix = pairwise_distances(X_scaled, metric="euclidean")

dist_df = pd.DataFrame(
    dist_matrix,
    index=ship_df["ship_id"],
    columns=ship_df["ship_id"]
)

print("\nPairwise ship distance matrix:")
print(dist_df.round(2))

dist_df.to_csv("C:/Users/student02/data/plots/ship_pairwise_distances.csv")

plt.figure(figsize=(8, 6))
sns.heatmap(
    dist_df,
    annot=True,
    cmap="viridis",
    fmt=".2f"
)
plt.title("Pairwise Distance Between Ships")
plt.xlabel("Ship ID")
plt.ylabel("Ship ID")
plt.tight_layout()
plt.savefig("C:/Users/student02/data/plots/ship_pairwise_distances.png")
plt.close()

print("\nNearest ships to each weak-predicted ship:")

for bad_ship in BAD_SHIPS:
    if bad_ship not in dist_df.index:
        continue

    distances = dist_df.loc[bad_ship].drop(index=bad_ship)
    nearest = distances.sort_values()

    print(f"\nShip {bad_ship}:")
    print(nearest)


target_group_stats = (
    df.groupby("prediction_group")["target_attained_index"]
    .agg(["count", "min", "max", "mean", "std"])
)

print("\nTarget stats for good-predicted vs bad-predicted ships:")
print(target_group_stats)

target_group_stats.to_csv(
    "C:/Users/student02/data/plots/good_vs_bad_target_stats.csv"
)

plt.figure(figsize=(8, 6))
sns.boxplot(
    data=df,
    x="prediction_group",
    y="target_attained_index",
    palette="viridis"
)
plt.title("Target Attained Index: Good-Predicted vs Bad-Predicted Ships")
plt.xlabel("Prediction group")
plt.ylabel("Target attained index")
plt.tight_layout()
plt.savefig("C:/Users/student02/data/plots/good_vs_bad_target_boxplot.png")
plt.close()
