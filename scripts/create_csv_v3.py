# Import standard library packages.
import sqlite3

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
