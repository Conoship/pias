import yaml
import pandas as pd
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

# Load Data
df = pd.read_csv("C:/Users/student01/Desktop/data/all_ships_baseline.csv")

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

# Data Split (80% train, 20% test)
X_Train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Load the hyperparameters configuration.
config = {}
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Initialize and Train the Model
xgb_params = config["XGBRegressorBaseline"]
model = XGBRegressor(**xgb_params)
model.fit(X_Train, y_train)
print("Model training complete.")

# Evaluate Performance
predictions = model.predict(X_test)
accuracy = r2_score(y_test, predictions)
error = mean_absolute_error(y_test, predictions)

print(f"Model Performance")
print(f"R-squared score: {accuracy:.4f}")
print(f"Average Error (m): {error:.4f}")
