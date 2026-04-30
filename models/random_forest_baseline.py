import yaml
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, learning_curve


# Save the model
def save_model(model):
    with open("model.pkl", "wb") as f:
        pickle.dump(model, f)


def plot_results(model, X, y, y_test, preds, errors, r2, mae):
    # Accuracy with R2 Label
    plt.figure(figsize=(8, 6))
    plt.scatter(y_test, preds, alpha=0.6, color="blue")
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--")
    plt.text(
        0.05,
        0.9,
        f"$R^2 Score: {r2:.3f}$\nAvg Error: {mae:.4f}",
        transform=plt.gca().transAxes,
        fontsize=12,
        bbox=dict(facecolor="white", alpha=0.7),
    )
    plt.title("Attained Index: Predicted vs Actual")
    plt.xlabel("Actual Attained Index")
    plt.ylabel("Predicted Attained Index")
    plt.tight_layout()
    plt.savefig("plots/rf_attained_accuracy_v3.png")

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
    plt.savefig("plots/rf_learning_curve_v3.png")

    # Residuals
    plt.figure(figsize=(8, 6))
    plt.scatter(preds, errors, alpha=0.6, color="purple")
    plt.axhline(0, color="black", linestyle="-")
    plt.title("Residuals (Error Patterns)")
    plt.xlabel("Predicted Attained Index")
    plt.ylabel("Error")
    plt.tight_layout()
    plt.savefig("plots/rf_attained_residuals_v3.png")

    plt.show()


# Load Data and Initial Clean
df = pd.read_csv("C:/Users/student02/data/all_ships_light_v4.csv")
cols_to_drop = [
    "target_margin",
    "target_attained_index",
    "ship_version_id",
    "condition_code",
]

X = df.select_dtypes(include=["number"]).drop(columns=cols_to_drop, errors="ignore")
y = df["target_attained_index"]

groups = df["ship_version_id"]

# Load the hyperparameters configuration.
config = {}
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Filter Low-Impact Variables
low_impact_random_forest_params = config["LowImpactRandomForestRegressor"]
temp_rf = RandomForestRegressor(**low_impact_random_forest_params).fit(X, y)
important_cols = X.columns[temp_rf.feature_importances_ > 0.01]
X = X[important_cols]

gkf = GroupKFold(n_splits=5)
r2_scores = []
mae_scores = []
for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups=groups)):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    # Model Training
    random_forest_params = config["RandomForestRegressor"]
    model = RandomForestRegressor(**random_forest_params)
    model.fit(X_train, y_train)

    # Evaluate Performance
    predictions = model.predict(X_test)
    accuracy = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)

    r2_scores.append(accuracy)
    mae_scores.append(mae)

    print(f"Fold {fold + 1}")
    print(f"R2: {predictions}")
    print(f"MAE: {mae}")

print(f"Model Performance")
print(f"Mean R2: {sum(r2_scores) / len(r2_scores):.4f}")
print(f"Mean MAE: {sum(mae_scores) / len(mae_scores):.4f}")

# Predictions and Errors
preds = model.predict(X_test)
r2 = r2_score(y_test, preds)
mae = mean_absolute_error(y_test, preds)
errors = y_test - preds

plot_results(model, X, y, y_test, preds, errors, r2, mae)
