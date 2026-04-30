import yaml
import pandas as pd
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error

# Load Data
df = pd.read_csv("C:/Users/student01/Desktop/data/all_ships_light_v4.csv")

# Define Features (X) and Target (y)
features = [
    "draft",
    "vcg",
    "displacement",
    "condition_code",
    "trim",
    "openings_per_compartment",
    "total_compartments",
]
X = df[features]
y = df["target_margin"]

groups = df["ship_version_id"]

# Load the hyperparameters configuration.
config = {}
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Initialize and Train the Model
xgb_params = config["XGBRegressorBaseline"]

# Cross-validation
gkf = GroupKFold(n_splits=5)
r2_scores = []
mae_scores = []
for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups=groups)):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model = XGBRegressor(**xgb_params)
    model.fit(
        X_train, 
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False)
    print("Model training complete.")

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
