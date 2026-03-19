import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load the clean csv
df = pd.read_csv('C:/Users/student01/Desktop/data/all_ships_baseline_clean.csv')

# Correlation between core hydrostatics and the stability margin
plt.figure(figsize=(10, 8))
cols = ['draft', 'vcg', 'displacement', 'total_compartments', 'target_margin']
sns.heatmap(df[cols].corr(), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Matrix: Hydrostatics vs Stability Margin')
plt.savefig('C:/Users/student01/Desktop/data/plots/all_ships/all_ships_correlation.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

# Pairplot of core hydrostatics colored by loading condition
pair_plot = sns.pairplot(df, vars=['draft', 'vcg', 'displacement', 'target_margin'], hue='condition_code')
pair_plot.fig.suptitle('Pairwise Relationships Grouped By Loading Condition', y=1.02)
plt.savefig('C:/Users/student01/Desktop/data/plots/all_ships/all_ships_pairplot.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

# Distribution of the target margin relative to the safety limit
plt.figure(figsize=(10, 6))
sns.histplot(df['target_margin'], kde=True)
plt.axvline(0, color='red', linestyle='--')
plt.title('Distribution of Target Stability Margins (Safety Threshold at 0)')
plt.savefig('C:/Users/student01/Desktop/data/plots/all_ships/all_ships_margin_dist.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

# Feature Importance
plt.figure(figsize=(10, 6))
importance = df[cols].corr()['target_margin'].abs().sort_values(ascending=False).drop('target_margin')
sns.barplot(x=importance.values, y=importance.index, palette='magma')
plt.title('Statistical Importance: Variables Driving Stability Margin')
plt.savefig('C:/Users/student01/Desktop/data/plots/all_ships/all_ships_statistical_importance.png')
plt.close()
print("Figure was saved!")
