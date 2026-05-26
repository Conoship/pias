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


def get_existing_ship_and_version_id(conn, ship, design, version, subversion, ship_run):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.id, sv.id
        FROM ship_version sv
        JOIN ship s ON s.id = sv.ship_id
        WHERE s.name = ?
            AND sv.design_name = ?
            AND sv.version = ?
            AND sv.subversion = ?
            AND sv.ship_run = ?
        """,
        (ship, design, version, subversion, ship_run),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(
            "No existing ship_version found for "
            f"ship={ship}, design={design}, version={version}, "
            f"subversion={subversion}, ship_run={ship_run}"
        )
    return row[0], row[1]


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
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        print(f"Using database: {db_path}")
        print(
            "Looking for ship_version: "
            f"ship={ship}, design={design}, version={version}, "
            f"subversion={subversion}, ship_run={ship_run}"
        )
        print(
            "Parsed dimensions: "
            f"lpp={lpp}, loa={loa}, breadth={breadth}, depth={depth}"
        )

        ship_id, ship_version_id = get_existing_ship_and_version_id(
            conn, ship, design, version, subversion, ship_run
        )

        cur = conn.cursor()
        cur.execute(
            """
            UPDATE main_dimensions
            SET id = ?,
                lpp = ?,
                loa = ?,
                breadth = ?,
                depth = ?
            WHERE ship_version_id = ?
            """,
            (ship_id, lpp, loa, breadth, depth, ship_version_id),
        )

        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO main_dimensions
                    (id, ship_version_id, lpp, loa, breadth, depth)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ship_id, ship_version_id, lpp, loa, breadth, depth),
            )

        conn.commit()
        print(
            "Main dimensions imported "
            f"for ship_id={ship_id}, ship_version_id={ship_version_id}"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.parsing.dimensions.parse_main_dimensions_local <rtf_path>")
        sys.exit(1)

    import_main_dimensions_rtf_local(sys.argv[1])
