import re
import psycopg
from pathlib import Path
import pdfplumber

import os
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return psycopg.connect(
        dbname=os.environ["PG_DBNAME"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        host=os.environ["PG_HOST"],
        port=int(os.environ["PG_PORT"]),
    )


def parse_filename(path):
    name = Path(path).name
    stem = Path(name).stem

    # strip optional "_probdam" suffix before extension
    if stem.lower().endswith("_probdam"):
        stem = stem[: -len("_probdam")]

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
        return float(str(text).strip())
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


def detect_side(first_page_text: str):
    m = re.search(r"Damage at\s+([A-Z]+)", first_page_text)
    return m.group(1) if m else None


def parse_damage_row(row, ship_version_id, side, cur):
    if not row or row[0] is None:
        return

    first = (row[0] or "").strip()
    # damage case pattern "1.1", "2.3", etc.
    if not re.match(r"^\d+\.\d+$", first):
        return

    # normalise row length
    if len(row) > 12:
        row = row[:12]
    while len(row) < 12:
        row.append(None)

    damage_case = first
    aft = parse_float(row[1])
    fwd = parse_float(row[2])
    inside = parse_float(row[3])
    upper = parse_float(row[4])
    pi_l = parse_float(row[5])
    si_l = parse_float(row[6])
    pi_p = parse_float(row[7])
    si_p = parse_float(row[8])
    pi_d = parse_float(row[9])
    si_d = parse_float(row[10])
    ai = parse_float(row[11])

    cur.execute(
        """
        INSERT INTO probdam_case (
          ship_version_id,
          side,
          damage_case,
          aft_boundary,
          fwd_boundary,
          inside_boundary,
          upper_boundary,
          pi_tlight,
          si_tlight,
          pi_tpartial,
          si_tpartial,
          pi_tdeepest,
          si_tdeepest,
          ai
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            ship_version_id,
            side,
            damage_case,
            aft,
            fwd,
            inside,
            upper,
            pi_l,
            si_l,
            pi_p,
            si_p,
            pi_d,
            si_d,
            ai,
        ),
    )


def parse_total(row, ship_version_id, side, cur):
    if not row or row[0] is None:
        return
    if not str(row[0]).strip().startswith("Total"):
        return

    nums = [parse_float(c) for c in row[1:] if c is not None]
    while len(nums) < 4:
        nums.append(None)

    cur.execute(
        """
        INSERT INTO probdam_total (
          ship_version_id,
          side,
          total_pi_tlight,
          total_pi_tpartial,
          total_pi_tdeepest,
          total_ai
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ship_version_id, side, nums[0], nums[1], nums[2], nums[3]),
    )


def parse_damage_line(line: str, ship_version_id, side, cur):
    line = (line or "").strip()
    if not line:
        return

    parts = line.split()
    if not parts:
        return

    if not re.match(r"^\d+\.\d+$", parts[0]):
        return

    row = parts[:]
    parse_damage_row(row, ship_version_id, side, cur)


def parse_total_line(line: str, ship_version_id, side, cur):
    line = (line or "").strip()
    if not line:
        return

    parts = line.split()
    if not parts or not parts[0].startswith("Total"):
        return

    parse_total(parts, ship_version_id, side, cur)


def _find_float(pattern: str, text: str):
    m = re.search(pattern, text)
    return parse_float(m.group(1)) if m else None


def parse_trim_gm_block(text, block_title, condition_name, ship_version_id, cur):
    """
    Extracts one of:
      - Light service draft
      - Partial subdivision draft
      - Deepest subdivision draft
    from the ProbDam summary page.
    """
    # grab from the block_title up to a blank line or end
    m = re.search(re.escape(block_title) + r".*?(?:\n\s*\n|$)", text, flags=re.DOTALL)
    if not m:
        return
    block = m.group(0)

    draft = _find_float(r"Intact draft\s*=\s*([-\d\.]+)\s*m", block)
    trim = _find_float(r"Intact trim\s*=\s*([-\d\.]+)\s*m", block)
    vcg = _find_float(r"Intact VCG'\s*=\s*([-\d\.]+)\s*m", block)
    mg = _find_float(r"MG'\s*=\s*([-\d\.]+)\s*m", block)
    disp = _find_float(r"Intact displacement\s*=\s*([-\d\.]+)\s*ton", block)
    a_val = _find_float(r"Subdivision index A\s*=\s*([-\d\.]+)", block)
    req = _find_float(r"\([<>]\s*([-\d\.]+)\)", block)

    cur.execute(
        """
        INSERT INTO trim_gm (
          ship_version_id,
          condition_name,
          draft,
          trim,
          vcg,
          mg,
          displacement,
          attained_index,
          required_index
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (ship_version_id, condition_name) DO UPDATE SET
          draft = EXCLUDED.draft,
          trim = EXCLUDED.trim,
          vcg = EXCLUDED.vcg,
          mg = EXCLUDED.mg,
          displacement = EXCLUDED.displacement,
          attained_index = EXCLUDED.attained_index,
          required_index = EXCLUDED.required_index
        """,
        (
            ship_version_id,
            condition_name,
            draft,
            trim,
            vcg,
            mg,
            disp,
            a_val,
            req,
        ),
    )


def parse_conclusion(text, ship_version_id, cur):
    m_len = re.search(r"Subdivision length\s*=\s*([-\d\.]+)\s*m", text)
    m_r = re.search(r"Required subdivision index R\s*=\s*([-\d\.]+)", text)
    m_a = re.search(r"Attained subdivision index A\s*=\s*([-\d\.]+)", text)

    if not (m_len and m_r and m_a):
        return

    length = parse_float(m_len.group(1))
    req_r = parse_float(m_r.group(1))
    att_a = parse_float(m_a.group(1))
    complies = "does NOT comply" not in text

    cur.execute(
        """
        INSERT INTO probdam_conclusion (
          ship_version_id,
          subdivision_length,
          required_index,
          attained_index,
          complies
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        (ship_version_id, length, req_r, att_a, complies),
    )


def import_probdam_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    ship_name, design_name, version, subversion = parse_filename(pdf_path)

    conn = get_conn()
    try:
        ship_id = get_ship(conn, ship_name)
        ship_version_id = get_version(conn, ship_id, design_name, version, subversion)

        with conn.cursor() as cur, pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            side = detect_side(first_text)

            # Parse damage cases and totals from page text
            for page in pdf.pages:
                text = page.extract_text() or ""
                for raw_line in text.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue

                    if "Damage case" in line or "boundary" in line:
                        continue

                    if line.startswith("Total"):
                        parse_total_line(line, ship_version_id, side, cur)
                    else:
                        parse_damage_line(line, ship_version_id, side, cur)

            # Penultimate page: trim & GM summary (light/partial/deepest)
            if len(pdf.pages) >= 2:
                summary_text = pdf.pages[-2].extract_text() or ""
                parse_trim_gm_block(
                    summary_text, "Light service draft", "light", ship_version_id, cur
                )
                parse_trim_gm_block(
                    summary_text,
                    "Partial subdivision draft",
                    "partial",
                    ship_version_id,
                    cur,
                )
                parse_trim_gm_block(
                    summary_text,
                    "Deepest subdivision draft",
                    "deepest",
                    ship_version_id,
                    cur,
                )

            # Last page: compliance / conclusion
            last_text = pdf.pages[-1].extract_text() or ""
            parse_conclusion(last_text, ship_version_id, cur)

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parseProbdam.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    import_probdam_pdf(pdf_path)
    print("Probdam import completed.")
