import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_absolute_error

df = pd.read_csv('C:/Users/student02/data/allships.csv')

# Group versions by ship test for now before the dianostic
df['ship_id'] = df['ship_version_id'].astype(str).str[0]
print("Ships found:", df['ship_id'].unique())

features = [
    'draft', 'trim', 'mg', 'displacement', 'vcg', 'condition_code',
    'total_compartments', 'avg_permeability', 'openings_per_compartment',
    'subdivision_length',
    'total_layout_length', 'max_layout_breadth', 'max_layout_height',
    'avg_cross_section', 'sum_bh_sections', 'std_breadth', 'std_height',
    'n_frustum_points'
]

# Only keep features in the CSV
features = [f for f in features if f in df.columns]
print("Features used:", features)

X = df[features]
y = df['target_attained_index']

# Leave one ship out 
ships = df['ship_id'].unique()
results = []

for test_ship in ships:
    train_mask = df['ship_id'] != test_ship
    test_mask  = df['ship_id'] == test_ship

    X_train = X[train_mask]
    y_train = y[train_mask]
    X_test  = X[test_mask]
    y_test  = y[test_mask]

    model = XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    r2  = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)

    results.append({'test_ship': test_ship, 'r2': r2, 'mae': mae})
    print(f"Ship {test_ship} held out → R: {r2:.4f} | MAE: {mae:.4f}")

# Summary
results_df = pd.DataFrame(results)
print(f"\n--- Cross-validation summary ---")
print(f"Mean R:  {results_df['r2'].mean():.4f}")
print(f"Mean MAE: {results_df['mae'].mean():.4f}")