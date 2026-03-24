import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load the clean csv
df = pd.read_csv('C:/Users/student02/data/all_light_v2.csv')

# Correlation between core hydrostatics and the stability margin
plt.figure(figsize=(10, 8))
cols = ['target_attained_index',
 'openings_per_compartment',
    'total_compartments', 'subdivision_length', 'avg_permeability',

    'n_cargo','n_ballast','n_cargohold_hatch', 'n_potable_water','n_gas_oil','n_void','n_fuel_oil',

    'total_layout_length','max_layout_breadth','max_layout_height','avg_cross_section','sum_bh_sections','std_breadth','std_height','n_frustum_points','std_breadth'
]
sns.heatmap(df[cols].corr(), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Matrix: Hydrostatics vs Stability Margin')
plt.savefig('C:/Users/student02/data/plots/all_ships_correlation.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

# Pairplot of core hydrostatics colored by loading condition
pair_plot = sns.pairplot(df, vars= ['target_attained_index',
 'openings_per_compartment',
    'total_compartments', 'subdivision_length', 'avg_permeability',

    'n_cargo','n_ballast','n_cargohold_hatch', 'n_potable_water','n_gas_oil','n_void','n_fuel_oil',

    'total_layout_length','max_layout_breadth','max_layout_height','avg_cross_section','sum_bh_sections','std_breadth','std_height','n_frustum_points','std_breadth'
], hue='condition_code')
pair_plot.fig.suptitle('Pairwise Relationships Grouped By Loading Condition', y=1.02)
plt.savefig('C:/Users/student02/data/plots/all_ships_pairplot.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

# Distribution of the target margin relative to the safety limit
plt.figure(figsize=(10, 6))
sns.histplot(df['target_attained_index'], kde=True)
plt.axvline(0, color='red', linestyle='--')
plt.title('Distribution of Target Stability Margins (Safety Threshold at 0)')
plt.savefig('C:/Users/student02/data/plots/all_ships_margin_dist.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

# Feature Importance
plt.figure(figsize=(10, 6))
importance = df[cols].corr()['target_attained_index'].abs().sort_values(ascending=False).drop('target_attained_index')
sns.barplot(x=importance.values, y=importance.index, palette='magma')
plt.title('Statistical Importance: Variables Driving Stability Margin')
plt.savefig('C:/Users/student02/data/plots/all_ships_statistical_importance.png')
plt.close()
print("Figure was saved!")

plt.figure(figsize=(8, 5))
df.boxplot(column='target_attained_index', by='ship_id')
plt.title('Attained Index Distribution by Ship')
plt.suptitle('')
plt.xlabel('Ship ID')
plt.ylabel('Attained Index A')
plt.tight_layout()
plt.savefig('C:/Users/student02/data/plots/a_by_ship.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")

plt.figure(figsize=(8, 5))
df.boxplot(column='target_attained_index', by='condition_code')
plt.title('Attained Index by Loading Condition')
plt.suptitle('')
plt.xticks([1, 2, 3], ['Light', 'Partial', 'Deepest'])
plt.xlabel('Loading Condition')
plt.ylabel('Attained Index A')
plt.tight_layout()
plt.savefig('C:/Users/student02/data/plots/a_by_condition.png', dpi=300, bbox_inches='tight')
plt.close()
print("Figure was saved!")