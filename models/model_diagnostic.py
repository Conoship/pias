import pandas as pd

df = pd.read_csv("your_file.csv")

# 1. How many rows per ship version?
print(df['ship_version_id'].value_counts().head(20))

# 2. Target distribution
print("\nTarget stats:")
print(df['target_margin'].describe())

# 3. How much does the target actually vary?
print("\nTarget variance by ship_version_id:")
print(df.groupby('ship_version_id')['target_margin'].std().describe())

# 4. Correlation of each feature with target
print("\nCorrelations with target:")
print(df[['draft','trim','mg','displacement','vcg',
          'condition_code','openings_per_compartment',
          'total_compartments','subdivision_length',
          'avg_permeability','target_margin']].corr()['target_margin'].sort_values())