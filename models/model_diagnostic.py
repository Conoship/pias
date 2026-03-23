import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the data
df = pd.read_csv('C:/Users/student02/data/allships.csv')

# 1. How many rows per ship version? (should be 3)
print("Total rows:", len(df))
print("\nRows per ship version (first 10):")
print(df['ship_version_id'].value_counts().head(10))

# 2. Target distribution
print("\nTarget stats:")
print(df['target_margin'].describe())

# 3. How much does the target vary within each ship version?
print("\nTarget variance by ship_version_id:")
print(df.groupby('ship_version_id')['target_margin'].std().describe())

# 4. Correlation of each feature with the target
features = [
    'draft', 'trim', 'mg', 'displacement', 'vcg',
    'condition_code', 'openings_per_compartment',
    'total_compartments', 'subdivision_length', 'avg_permeability'
]
features = [f for f in features if f in df.columns]

correlations = df[features + ['target_margin']].corr()['target_margin'].drop('target_margin')
correlations = correlations.abs().sort_values(ascending=False)

print("\nCorrelation of each feature with target:")
print(correlations)

# 5. Plot the correlations
plt.figure(figsize=(10, 6))
sns.barplot(x=correlations.values, y=correlations.index, palette='viridis')
plt.title('How strongly does each feature relate to the target?')
plt.xlabel('Correlation (0 = no relation, 1 = perfect relation)')
plt.tight_layout()
plt.savefig('C:/Users/student02/data/plots/feature_correlations.png')
plt.close()
print("\nPlot saved!")