import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances

df = pd.read_csv(
    "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_all_conditions_v5.csv"
)

output_dir = Path("C:/Users/student01/Desktop/rug-project/pias/plots/diagnostics")
output_dir.mkdir(parents=True, exist_ok=True)

# df = df[df["condition_code"] == 0].copy()  # light
# df = df[df["condition_code"] == 1].copy()  # partial
# df = df[df["condition_code"] == 2].copy()  # deepest

similarity_features = [
    # Loading / stability features
    "draft",
    "trim",
    "mg",
    "displacement",
    "vcg",
    "condition_code",
    # Compartment features
    "openings_per_compartment",
    "total_compartments",
    "avg_permeability",
    # Compartment content counts
    "n_cargo",
    "n_ballast",
    "n_cargohold_hatch",
    "n_potable_water",
    "n_gas_oil",
    "n_void",
    "n_fuel_oil",
    # Geometry features
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

print("/nSimilarity features used:")
print(similarity_features)

ship_df = df.groupby("ship_id")[similarity_features].agg(["mean", "std", "min", "max"])

ship_df.columns = [f"{col}_{stat}" for col, stat in ship_df.columns]
ship_df = ship_df.reset_index()

print("/nShip-level feature table:")
print(ship_df)

numeric_cols = ship_df.select_dtypes(include=["number"]).columns.tolist()
numeric_cols = [c for c in numeric_cols if c != "ship_id"]

X_ship = ship_df[numeric_cols].copy()
X_ship = X_ship.replace([np.inf, -np.inf], np.nan)
X_ship = X_ship.fillna(X_ship.median())

# Drop constant columns because they do not help distance calculations
constant_cols = [col for col in X_ship.columns if X_ship[col].nunique(dropna=True) <= 1]

if constant_cols:
    print("/nDropping constant columns:")
    print(constant_cols)
    X_ship = X_ship.drop(columns=constant_cols)

# Standardize so all features are compared fairly
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_ship)

X_scaled_df = pd.DataFrame(X_scaled, index=ship_df["ship_id"], columns=X_ship.columns)

dist_matrix = pairwise_distances(X_scaled_df, metric="euclidean")

dist_df = pd.DataFrame(dist_matrix, index=X_scaled_df.index, columns=X_scaled_df.index)

print("/nPairwise ship distance matrix:")
print(dist_df.round(2))

plt.figure(figsize=(8, 6))
sns.heatmap(dist_df, annot=True, cmap="viridis", fmt=".2f")
plt.title("Pairwise Distance Between Ships")
plt.xlabel("Ship ID")
plt.ylabel("Ship ID")
plt.tight_layout()
plt.savefig(output_dir / "ship_pairwise_distances.png")
plt.close()

isolation_rows = []

for ship_id in dist_df.index:
    distances = dist_df.loc[ship_id].drop(index=ship_id)

    isolation_rows.append(
        {
            "ship_id": ship_id,
            "mean_distance_to_others": distances.mean(),
            "nearest_ship": distances.idxmin(),
            "nearest_distance": distances.min(),
            "farthest_ship": distances.idxmax(),
            "farthest_distance": distances.max(),
        }
    )

isolation_df = pd.DataFrame(isolation_rows)
isolation_df = isolation_df.sort_values("mean_distance_to_others", ascending=False)

print("/nShip isolation ranking:")
print(isolation_df)

plt.figure(figsize=(9, 5))
sns.barplot(data=isolation_df, x="ship_id", y="mean_distance_to_others")
plt.title("Ship Isolation Score")
plt.xlabel("Ship ID")
plt.ylabel("Mean distance to other ships")
plt.tight_layout()
plt.savefig(output_dir / "ship_isolation_scores.png")
plt.close()

feature_ranges = X_scaled_df.max(axis=0) - X_scaled_df.min(axis=0)
top_profile_features = feature_ranges.sort_values(ascending=False).head(20).index

profile_df = X_scaled_df[top_profile_features]

plt.figure(figsize=(14, 7))
sns.heatmap(profile_df, annot=True, cmap="coolwarm", center=0, fmt=".2f")
plt.title("Ship Feature Profile Heatmap")
plt.xlabel("Feature")
plt.ylabel("Ship ID")
plt.tight_layout()
plt.savefig(output_dir / "ship_profile_heatmap.png")
plt.close()

print("/nTop features shown in ship_profile_heatmap.png:")
print(list(top_profile_features))

pca = PCA(n_components=2)
pca_coords = pca.fit_transform(X_scaled_df)

pca_df = pd.DataFrame(
    {
        "ship_id": X_scaled_df.index,
        "PC1": pca_coords[:, 0],
        "PC2": pca_coords[:, 1],
    }
)

print("/nPCA explained variance:")
print(f"PC1:   {pca.explained_variance_ratio_[0]:.3f}")
print(f"PC2:   {pca.explained_variance_ratio_[1]:.3f}")
print(f"Total: {pca.explained_variance_ratio_[:2].sum():.3f}")

plt.figure(figsize=(8, 6))
sns.scatterplot(data=pca_df, x="PC1", y="PC2", s=130)

for _, row in pca_df.iterrows():
    plt.text(
        row["PC1"] + 0.03, row["PC2"] + 0.03, str(int(row["ship_id"])), fontsize=11
    )

plt.title("Ship Similarity Map using PCA")
plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)")
plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)")
plt.tight_layout()
plt.savefig(output_dir / "ship_similarity_pca.png")
plt.close()

pairs = []

ships = list(dist_df.index)

for i in range(len(ships)):
    for j in range(i + 1, len(ships)):
        ship_a = ships[i]
        ship_b = ships[j]

        pairs.append(
            {
                "ship_a": ship_a,
                "ship_b": ship_b,
                "distance": dist_df.loc[ship_a, ship_b],
            }
        )

pairs_df = pd.DataFrame(pairs)

most_similar_pair = pairs_df.sort_values("distance").iloc[0]
most_different_pair = pairs_df.sort_values("distance", ascending=False).iloc[0]

print("/nMost similar ship pair:")
print(most_similar_pair)

print("/nMost different ship pair:")
print(most_different_pair)


def explain_pair_difference(ship_a, ship_b, top_n=10):
    diff = (X_scaled_df.loc[ship_a] - X_scaled_df.loc[ship_b]).abs()
    diff = diff.sort_values(ascending=False).head(top_n)

    print(f"/nTop feature differences between Ship {ship_a} and Ship {ship_b}:")
    print(diff)


explain_pair_difference(most_similar_pair["ship_a"], most_similar_pair["ship_b"])

explain_pair_difference(most_different_pair["ship_a"], most_different_pair["ship_b"])

if "target_attained_index" in df.columns:
    print("/nTarget attained index stats per ship:")
    print(
        df.groupby("ship_id")["target_attained_index"].agg(
            ["count", "min", "max", "mean", "std"]
        )
    )
