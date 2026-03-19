import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load the clean csv
df = pd.read_csv('clean_data/ship4_stability_baseline_clean.csv')

# Correlation Matrix
plt.figure(figsize=(12, 8))
sns.heatmap(df.corr(), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Feature Correlation Matrix')
plt.savefig('data_visualization/plots/correlation_heatmap_ship4_baseline.png', dpi=300, bbox_inches='tight')
plt.show()

# Permeability vs Target Margin
plt.figure(figsize=(10, 6))
sns.regplot(data=df, x='avg_permeability', y='target_margin', scatter_kws={'alpha':0.5, 'color': 'blue'}, line_kws={'color':'red'})
plt.title('Impact of Average Permeability on Stability Margin')
plt.grid(True, linestyle='--', alpha=0.6)
plt.savefig('data_visualization/plots/permeability_impact_ship4_baseline.png', dpi=300, bbox_inches='tight')
plt.show()

# Condition Code Boxplot
plt.figure(figsize=(10, 6))
sns.boxplot(data=df, x='condition_code', y='target_margin', palette='Set2')
plt.xticks([0, 1, 2], ['Light', 'Partial', 'Deepest'])
plt.title('Stability Margin by Loading Condition')
plt.savefig('data_visualization/plots/condition_comparison_ship4_baseline.png', dpi=300, bbox_inches='tight')
plt.show()