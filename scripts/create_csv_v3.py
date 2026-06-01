# Import standard library packages.
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
