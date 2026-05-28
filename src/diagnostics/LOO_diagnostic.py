import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances

datasets = {
    "light": "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_light_v5.csv",
    "partial": "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_partial_v5.csv",
    "deepest": "C:/Users/student01/Desktop/rug-project/pias/data/all_ships_deepest_v5.csv",
}

base_output_dir = Path("C:/Users/student01/Desktop/rug-project/pias/plots/diagnostics")
base_output_dir.mkdir(parents=True, exist_ok=True)


similarity_features = [
    # Loading / stability features
    "draft",
    "trim",
    "mg",
    "displacement",
    "vcg",
    # "condition_code",
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


for condition_name, csv_path in datasets.items():
    df = pd.read_csv(csv_path)

    output_dir = base_output_dir / condition_name
    output_dir.mkdir(parents=True, exist_ok=True)

    features = [f for f in similarity_features if f in df.columns]

    # One row per ship
    ship_df = df.groupby("ship_id")[features].agg(["mean", "std", "min", "max"])
    ship_df.columns = [f"{col}_{stat}" for col, stat in ship_df.columns]
    ship_df = ship_df.reset_index()

    numeric_cols = ship_df.select_dtypes(include=["number"]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != "ship_id"]

    X_ship = ship_df[numeric_cols].copy()
    X_ship = X_ship.replace([np.inf, -np.inf], np.nan)
    X_ship = X_ship.fillna(X_ship.median())
    X_ship = X_ship.fillna(0)

    # Drop constant columns
    constant_cols = [
        col for col in X_ship.columns if X_ship[col].nunique(dropna=True) <= 1
    ]
    X_ship = X_ship.drop(columns=constant_cols)

    if X_ship.shape[1] == 0:
        continue

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_ship)

    X_scaled_df = pd.DataFrame(
        X_scaled, index=ship_df["ship_id"], columns=X_ship.columns
    )

    dist_matrix = pairwise_distances(X_scaled_df, metric="euclidean")

    dist_df = pd.DataFrame(
        dist_matrix, index=X_scaled_df.index, columns=X_scaled_df.index
    )

    plt.figure(figsize=(8, 6))
    sns.heatmap(dist_df, annot=True, cmap="viridis", fmt=".2f")
    plt.title(f"{condition_name.capitalize()}: Pairwise Ship Distance")
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
            }
        )

    isolation_df = pd.DataFrame(isolation_rows)
    isolation_df = isolation_df.sort_values("mean_distance_to_others", ascending=False)

    plt.figure(figsize=(9, 5))
    sns.barplot(data=isolation_df, x="ship_id", y="mean_distance_to_others")
    plt.title(f"{condition_name.capitalize()}: Ship Isolation Score")
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
    plt.title(f"{condition_name.capitalize()}: Ship Feature Profile")
    plt.xlabel("Feature")
    plt.ylabel("Ship ID")
    plt.tight_layout()
    plt.savefig(output_dir / "ship_profile_heatmap.png")
    plt.close()

    if X_scaled_df.shape[0] >= 2:
        pca = PCA(n_components=2)
        pca_coords = pca.fit_transform(X_scaled_df)

        pca_df = pd.DataFrame(
            {
                "ship_id": X_scaled_df.index,
                "PC1": pca_coords[:, 0],
                "PC2": pca_coords[:, 1],
            }
        )

        plt.figure(figsize=(8, 6))
        sns.scatterplot(data=pca_df, x="PC1", y="PC2", s=130)

        for _, row in pca_df.iterrows():
            plt.text(
                row["PC1"] + 0.03,
                row["PC2"] + 0.03,
                str(int(row["ship_id"])),
                fontsize=11,
            )

        plt.title(f"{condition_name.capitalize()}: Ship Similarity PCA")
        plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)")
        plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)")
        plt.tight_layout()
        plt.savefig(output_dir / "ship_similarity_pca.png")
        plt.close()
