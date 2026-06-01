# Import standard library packages.
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

"""py -u -c "import sqlite3, pandas as pd; conn=sqlite3.connect('data/mockdata.db'); q='''SELECT COUNT(*) n FROM compartment comp JOIN subcompartment sub ON sub.compartment_id = comp.id JOIN subcompartment_shape ss ON ss.shape_guid = sub.shape_guid AND ss.ship_version_id = comp.ship_version_id JOIN frustum_point fp ON fp.subcompartment_shape_id = ss.id'''; print(pd.read_sql_query(q, conn))""""
"""py -u -c "import sqlite3, pandas as pd; conn=sqlite3.connect('data/mockdata.db'); [print(t, pd.read_sql_query(f'SELECT COUNT(*) n FROM {t}', conn).iloc[0,0]) for t in ['ship_version','compartment','subcompartment','subcompartment_shape','frustum_point','trim_gm']]""""
# Import local packages.
from src.features.training_features import (
    build_training_features,
)

DB_PATH = "data/mockdata.db"
OUTPUT_PATH = "data/all_ships_v8.csv"


def main(db_path: str = DB_PATH, output_path: str = OUTPUT_PATH) -> None:
    conn = sqlite3.connect(db_path)

    try:
        df = build_training_features(conn)
        print(df.head())
        df.to_csv(output_path, index=False)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
