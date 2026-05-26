import re
import sys
from pathlib import Path

from src.db.db import create_all_tables, get_local_conn
from src.invoke.run_invoke import (
    PROCESS_SHORT,
    extract_ship_rtf,
    find_info,
    normalize_name,
    numeric_version_from_token,
)
from src.parsing.layout.parse_layout_local import get_ship, get_version
from src.parsing.utils.rtf_utils import rtf_to_text


def get_ship_version_from_rtf_path(rtf_path):
    process, ship_folder, version_token, sub_index = find_info(
        str(rtf_path),
        ["Basic Design", "Concept Design", "Final Design"],
    )
    pias_ship = extract_ship_rtf(str(rtf_path))

    ship = normalize_name(ship_folder or "UnknownShip")
    design = PROCESS_SHORT.get(
        (process or "").strip().lower(),
        normalize_name(process or "UnknownProcess"),
    )
    version = numeric_version_from_token(version_token)
    subversion = str(sub_index if sub_index is not None else 1)
    ship_run = normalize_name(pias_ship) if pias_ship else ""

    return ship, design, version, subversion, ship_run


def parse_float(value):
    try:
        return float(value.replace(",", "."))
    except (AttributeError, ValueError):
        return None


def get_main_dimensions(text):
    def find(label):
        pattern = rf"{re.escape(label)}\s*:?\s*([-+]?\d+(?:[.,]\d+)?)"
        match = re.search(pattern, text, re.IGNORECASE)
        return parse_float(match.group(1)) if match else None

    return (
        find("Length between perpendiculars"),
        find("Length overall"),
        find("Moulded breadth"),
        find("Moulded depth"),
    )


def import_main_dimensions_rtf_local(rtf_path):
    rtf_path = Path(rtf_path)
    ship, design, version, subversion, ship_run = get_ship_version_from_rtf_path(
        rtf_path
    )

    with open(rtf_path, "r", encoding="latin-1", errors="ignore") as file:
        text = rtf_to_text(file.read())

    lpp, loa, breadth, depth = get_main_dimensions(text)

    conn = get_local_conn()
    create_all_tables(conn)

    try:
        ship_id = get_ship(conn, ship)
        ship_version_id = get_version(
            conn, ship_id, design, version, subversion, ship_run
        )

        cur = conn.cursor()
        cur.execute(
            "DELETE FROM main_dimensions WHERE ship_version_id = ?",
            (ship_version_id,),
        )
        cur.execute(
            """
            INSERT INTO main_dimensions
                (ship_version_id, lpp, loa, breadth, depth)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ship_version_id, lpp, loa, breadth, depth),
        )
        conn.commit()
        print(f"Main dimensions imported for ship_version_id={ship_version_id}")

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.parsing.dimensions.parse_main_dimensions_local <rtf_path>")
        sys.exit(1)

    import_main_dimensions_rtf_local(sys.argv[1])
