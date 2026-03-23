import re
import psycopg
from pathlib import Path
import pdfplumber

def get_conn():
    return psycopg.connect(
        dbname="pias_damage",
        user="intern_user",
        password="W!3uCXrdV^%JQ2",
        host="python.conoship.com",
        port=5432,
    )

def parse_filename(path):
    name = Path(path).name
    stem = Path(name).stem
    parts = stem.split('_')

    ship = parts[0] if len(parts) > 0 else "unknownship"
    design = parts[1] if len(parts) > 1 else "unknowndesign"
    version = parts[2] if len(parts) > 2 else "unknownversion"
    subversion = "_".join(parts[3:]) if len(parts) > 3 else ""

    return ship.strip(), design.strip(), version.strip(), subversion.strip()

def parse_float(text):
    if text is None:
        return None
    try:
        return float(text.strip())
    except ValueError:
        return None

def get_ship(conn, ship_name):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM ship WHERE name = %s", (ship_name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT INTO ship (name) VALUES (%s) RETURNING id", (ship_name,))
        ship_id = cur.fetchone()[0]
    conn.commit()
    return ship_id

def get_version(conn, ship_id, design_name, version, subversion):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM ship_version
            WHERE ship_id = %s
              AND design_name = %s
              AND version = %s
              AND subversion = %s
            """,
            (ship_id, design_name, version, subversion),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            INSERT INTO ship_version (ship_id, design_name, version, subversion)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (ship_id, design_name, version, subversion),
        )
        ship_version_id = cur.fetchone()[0]
    conn.commit()
    return ship_version_id

def get_main_dimensions(text: str):
    def find(pattern):
        m = re.search(pattern, text)
        return parse_float(m.group(1)) if m else None

    lpp = find(r"Length between perpendiculars\s*:\s*([0-9.]+)\s*m")
    loa = find(r"Length overall\s*:\s*([0-9.]+)\s*m")
    breadth = find(r"Moulded breadth\s*:\s*([0-9.]+)\s*m")
    depth = find(r"Moulded depth\s*:\s*([0-9.]+)\s*m")

    return lpp, loa, breadth, depth

def import_main_dimensions(pdf_path):
    pdf_path = Path(pdf_path)
    ship, design, version, subversion = parse_filename(pdf_path)

    conn = get_conn()
    try:
        ship_id = get_ship(conn, ship)
        ship_version_id = get_version(conn, ship_id, design, version, subversion)

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        lpp, loa, breadth, depth = get_main_dimensions(text)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO main_dimensions
                    (ship_version_id, lpp, loa, breadth, depth)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ship_version_id, lpp, loa, breadth, depth),
            )
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python parseMainDimensions.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    import_main_dimensions(pdf_path)
    print("Main dimensions imported successfully.")
