import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import learning_curve
from sklearn.metrics import r2_score, mean_absolute_error

# Load Data and Initial Clean
df = pd.read_csv(
    "C:/Users/student01/Desktop/data/all_ships_multiple_features_light_v3.csv"
)
cols_to_drop = [
    "target_margin",
    "target_attained_index",
    "ship_version_id",
    "condition_code",
]

X = df.select_dtypes(include=["number"]).drop(columns=cols_to_drop, errors="ignore")
y = df["target_attained_index"]

# Load the hyperparameters configuration.
config = {}
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Filter Low-Impact Variables
low_impact_random_forest_params = config["LowImpactRandomForestRegressor"]
temp_rf = RandomForestRegressor(**low_impact_random_forest_params).fit(X, y)
important_cols = X.columns[temp_rf.feature_importances_ > 0.01]
X = X[important_cols]

# Leave one ship out
ships = df["ship_id"].unique()
print(ships)
results = []

# Initialize variables to avoid PyLance Errors.
y_test = pd.Series(dtype=float)
preds = pd.Series(dtype=float)
model: RandomForestRegressor | None = None
errors = pd.Series(dtype=float)

for test_ship in ships:
    train_mask = df["ship_id"] != test_ship
    test_mask = df["ship_id"] == test_ship

    X_train = X[train_mask]
    y_train = y[train_mask]
    X_test = X[test_mask]
    y_test = y[test_mask]

    model = RandomForestRegressor(**low_impact_random_forest_params)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)
    mae = mean_absolute_error(y_test, preds)
    errors = y_test - preds

    results.append({"test_ship": test_ship, "r2": r2, "mae": mae})
    print(f"Ship {test_ship} held out -> R: {r2:.4f} | MAE: {mae:.4f}")

results_df = pd.DataFrame(results)

# Accuracy with R2 Label
plt.figure(figsize=(8, 6))
plt.scatter(y_test, preds, alpha=0.6, color="blue")
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--")
plt.text(
    0.05,
    0.9,
    f"$R^2 Score: {results_df['r2'].mean():.3f}$\nAvg Error: {results_df['mae'].mean():.4f}",
    transform=plt.gca().transAxes,
    fontsize=12,
    bbox=dict(facecolor="white", alpha=0.7),
)
plt.title("Attained Index: Predicted vs Actual")
plt.xlabel("Actual Attained Index")
plt.ylabel("Predicted Attained Index")
plt.tight_layout()
plt.savefig(
    "C:/Users/student01/Desktop/rug-project/pias/models/plots/rf_attained_accuracy_one_out_v3.png"
)

# R2 Learning Curve
train_sizes, train_scores, test_scores = learning_curve(
    model, X, y, cv=5, scoring="r2", train_sizes=np.linspace(0.1, 1.0, 5)
)
plt.figure(figsize=(8, 6))
plt.plot(train_sizes, np.mean(train_scores, axis=1), "o-", label="Training R2")
plt.plot(train_sizes, np.mean(test_scores, axis=1), "o-", label="Validation R2")
plt.title("R2 Performance vs Data Size")
plt.xlabel("Number of Samples")
plt.ylabel("R2 Score")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    "C:/Users/student01/Desktop/rug-project/pias/models/plots/rf_learning_curve_one_out_v3.png"
)

# Residuals
plt.figure(figsize=(8, 6))
plt.scatter(preds, errors, alpha=0.6, color="purple")
plt.axhline(0, color="black", linestyle="-")
plt.title("Residuals (Error Patterns)")
plt.xlabel("Predicted Attained Index")
plt.ylabel("Error")
plt.tight_layout()
plt.savefig(
    "C:/Users/student01/Desktop/rug-project/pias/models/plots/rf_attained_residuals_one_out_v3.png"
)

plt.show()
print(f"Final R2 for Attained Index: {results_df['r2'].mean():.3f}")
