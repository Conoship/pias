import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split

df = pd.read_csv('C:/Users/student02/data/all_loads_all_features.csv')

df_ship = df.copy()
df_ship = df_ship[df_ship['target_attained_index']>0.1].copy()

features = ['draft','trim','mg','displacement','vcg',
 'openings_per_compartment', 'avg_permeability',

    'n_cargo','n_ballast','n_cargohold_hatch', 'n_potable_water','n_gas_oil','n_void','n_fuel_oil',

    'total_layout_length','max_layout_breadth','max_layout_height','avg_cross_section','sum_bh_sections','std_breadth,std_height','n_frustum_points','std_breadth'
]

# Only keep features in the CSV
features = [f for f in features if f in df.columns]

X = df_ship[features]
y = df_ship['target_attained_index']

X_Train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize and Train the Model
model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42)
model.fit(X_Train, y_train)

# Evaluate Performance
predictions = model.predict(X_test)
accuracy = r2_score(y_test, predictions)
error = mean_absolute_error(y_test, predictions)


print(f"\n--- model summary ---")
print(f"Mean R:  {accuracy:.4f}")
print(f"Mean MAE: {error:.4f}")