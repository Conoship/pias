import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, learning_curve
from sklearn.metrics import r2_score, mean_absolute_error
import numpy as np

# Load Data and Initial Clean
df = pd.read_csv("C:/Users/student01/Desktop/data/all_ships_multiple_features_light_v3.csv")
cols_to_drop = ['target_margin', 
                'target_attained_index', 
                'ship_version_id',
                'condition_code'
]

X = df.select_dtypes(include=['number']).drop(columns=cols_to_drop, errors='ignore')
y = df['target_attained_index']

# Filter Low-Impact Variables
temp_rf = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y)
important_cols = X.columns[temp_rf.feature_importances_ > 0.01]
X = X[important_cols]

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Model Training
model = RandomForestRegressor(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# Predictions and Errors
preds = model.predict(X_test)
r2 = r2_score(y_test, preds)
mae = mean_absolute_error(y_test, preds)
errors = y_test - preds

# Accuracy with R2 Label
plt.figure(figsize=(8, 6))
plt.scatter(y_test, preds, alpha=0.6, color='blue')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.text(0.05, 0.9, f'$R^2 Score: {r2:.3f}$\nAvg Error: {mae:.4f}', 
            transform=plt.gca().transAxes, 
            fontsize=12,
            bbox=dict(facecolor='white', alpha=0.7))
plt.title('Attained Index: Predicted vs Actual')
plt.xlabel('Actual Attained Index')
plt.ylabel('Predicted Attained Index')
plt.tight_layout()
plt.savefig('C:/Users/student01/Desktop/rug-project/pias/models/plots/rf_attained_accuracy_v3.png')

# R2 Learning Curve
train_sizes, train_scores, test_scores = learning_curve(
    model, X, y, cv=5, scoring='r2', train_sizes=np.linspace(0.1, 1.0, 5)
)
plt.figure(figsize=(8, 6))
plt.plot(train_sizes, np.mean(train_scores, axis=1), 'o-', label="Training R2")
plt.plot(train_sizes, np.mean(test_scores, axis=1), 'o-', label="Validation R2")
plt.title('R2 Performance vs Data Size')
plt.xlabel('Number of Samples')
plt.ylabel('R2 Score')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('C:/Users/student01/Desktop/rug-project/pias/models/plots/rf_learning_curve_v3.png')

# Residuals
plt.figure(figsize=(8, 6))
plt.scatter(preds, errors, alpha=0.6, color='purple')
plt.axhline(0, color='black', linestyle='-')
plt.title('Residuals (Error Patterns)')
plt.xlabel('Predicted Attained Index')
plt.ylabel('Error')
plt.tight_layout()
plt.savefig('C:/Users/student01/Desktop/rug-project/pias/models/plots/rf_attained_residuals_v3.png')

plt.show()
print(f"Final R2 for Attained Index: {r2:.3f}")




