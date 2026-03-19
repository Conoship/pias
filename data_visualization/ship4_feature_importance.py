import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('C:/Users/student01/Desktop/data/ship4_stability_baseline_clean.csv')
loading_cols = ['draft', 'vcg', 'displacement', 'condition_code', 'target_margin']

importance = df[loading_cols].corr()['target_margin'].abs().sort_values(ascending=False).drop('target_margin')

plt.figure(figsize=(10, 6))
sns.barplot(x=importance.values, y=importance.index, palette='viridis')
plt.title('Importance: How Loading Conditions Drive Stability')
plt.savefig('C:/Users/student01/Desktop/data/plots/ship4_loading_features_importance.png')
plt.close()
print("File saved!")