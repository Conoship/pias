# Import standard library packages.
import sqlite3
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.training_features import (
    build_training_features,
)

DB_PATH = "localhost.db"
OUTPUT_PATH = "data/all_ships_v8.csv"


def main(db_path: str = DB_PATH, output_path: str = OUTPUT_PATH) -> None:
    conn = sqlite3.connect(db_path)
    start = time.perf_counter()
    print("Creating CSV v3...", flush=True)
    print(f"Opening database: {db_path}", flush=True)

    conn = sqlite3.connect(db_path)

    try:
        df = build_training_features(conn, verbose=True)
        print(df.head())
        print(f"Writing CSV: {output_path}", flush=True)
        df.to_csv(output_path, index=False)
        seconds = time.perf_counter() - start
        print(f"Done: {len(df)} rows in {seconds:.1f}s", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
