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

    # strip optional "_openings" suffix before extension
    if stem.lower().endswith("_openings"):
        stem = stem[: -len("_openings")]

    parts = stem.split("_")

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


def import_openings(pdf_path):
    pdf_path = Path(pdf_path)
    ship_name, design_name, version, subversion = parse_filename(pdf_path)

    conn = get_conn()
    try:
        ship_id = get_ship(conn, ship_name)
        ship_version_id = get_version(conn, ship_id, design_name, version, subversion)

        with conn.cursor() as cur, pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        if not row or all(cell is None for cell in row):
                            continue

                        # header row
                        if row[0] and "Description" in row[0]:
                            continue

                        if len(row) < 6:
                            continue

                        description = (row[0] or "").strip()
                        length = parse_float(row[1])
                        breadth = parse_float(row[2])
                        height = parse_float(row[3])
                        opening_type = (row[4] or "").strip()
                        connected = (row[5] or "").strip()

                        compartment_id = None
                        if connected and connected != "-":
                            cur.execute(
                                """
                                SELECT id
                                FROM compartment
                                WHERE ship_version_id = %s
                                  AND name = %s
                                """,
                                (ship_version_id, connected),
                            )
                            r = cur.fetchone()
                            if r:
                                compartment_id = r[0]

                        cur.execute(
                            """
                            INSERT INTO opening
                                (ship_version_id,
                                 compartment_id,
                                 description,
                                 length,
                                 breadth,
                                 height,
                                 opening_type,
                                 connected_compartment)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                ship_version_id,
                                compartment_id,
                                description,
                                length,
                                breadth,
                                height,
                                opening_type,
                                connected,
                            ),
                        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parseOpenings.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    import_openings(pdf_path)
    print("Openings import completed.")
