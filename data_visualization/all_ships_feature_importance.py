import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("C:/Users/student02/data/allships.csv")
loading_cols = [
    "draft",
    "vcg",
    "displacement",
    "condition_code",
    "trim",
    "openings_per_compartment",
    "total_compartments",
    "target_margin",
]

# Importance for loading factors only
importance = (
    df[loading_cols]
    .corr()["target_margin"]
    .abs()
    .sort_values(ascending=False)
    .drop("target_margin")
)

# Statistical Importance Loading Factors Only
plt.figure(figsize=(10, 6))
sns.barplot(x=importance.values, y=importance.index, palette="viridis")
plt.title("Importance: How Loading Conditions Drive Stability")
plt.savefig("C:/Users/student02/data/plots/all_ships_loading_features_importance.png")
plt.close()
print("File saved!")
