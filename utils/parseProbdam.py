import re
from pathlib import Path

import psycopg


# ---------- DB CONNECTION ----------


def get_conn():
    return psycopg.connect(
        dbname="pias_damage",
        user="intern_user",
        password="W!3uCXrdV^%JQ2",
        host="python.conoship.com",
        port=5432,
    )


# ---------- FILENAME PARSING ----------


def parse_filename(path: str):
    """
    Expect names like:
      <ship>_<design>_<version>_<subversion>_probdam.rtf
    Extra parts after the 4th are joined as subversion.
    """
    name = Path(path).name
    stem = Path(name).stem

    # strip optional "_probdam" suffix
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
    t = str(text).strip()
    if not t or t.upper() in ("INF", "-INF", "NAN", "-"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


# ---------- SHIP / VERSION HELPERS ----------


def get_ship(conn, ship_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM ship WHERE name = %s", (ship_name,))
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            "INSERT INTO ship (name) VALUES (%s) RETURNING id",
            (ship_name,),
        )
        ship_id = cur.fetchone()[0]
    conn.commit()
    return ship_id


def get_version(conn, ship_id, design_name, version, subversion, ship_run):
    """
    Matches your existing ship_version(unique ship_id, design_name, version, subversion)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM ship_version
            WHERE ship_id = %s
              AND design_name = %s
              AND version = %s
              AND subversion = %s
              AND ship_run = %s
            """,
            (ship_id, design_name, version, subversion, ship_run),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            INSERT INTO ship_version (ship_id, design_name, version, subversion, ship_run)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ship_id, design_name, version, subversion, ship_run),
        )
        ship_version_id = cur.fetchone()[0]
    conn.commit()
    return ship_version_id


# ---------- TEXT PARSING HELPERS ----------


def detect_side(text: str):
    """
    Look for 'Damage at PS.' or 'Damage at SB.' etc and return 'PS', 'SB', ...
    """
    m = re.search(r"Damage at\s+([A-Z]+)", text)
    return m.group(1) if m else None


def _find_float(pattern: str, text: str):
    m = re.search(pattern, text)
    return parse_float(m.group(1)) if m else None


# ---------- PROBDAM CASES / TOTAL ----------


def parse_damage_row(row, ship_version_id, side, cur):
    """
    row = [damage_case, aft, fwd, inside, upper,
           pi_tlight, si_tlight, pi_tpartial, si_tpartial,
           pi_tdeepest, si_tdeepest, ai]
    """
    if not row or row[0] is None:
        return

    first = (row[0] or "").strip()
    if not re.match(r"^\d+\.\d+$", first):
        return

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
    """
    Insert the 'Total' line into probdam_total.
    RTF line looks like (after cleanup):

      Total   0.8855  0.8664  0.8457  0.4890
    """
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

    parse_damage_row(parts, ship_version_id, side, cur)


def parse_total_line(line: str, ship_version_id, side, cur):
    """
    In your RTF the 'Total' line is polluted by some shape info before 'Total',
    e.g.:

      *shapeType20lineWidth... Total    0.8855 ...

    So we first cut from 'Total' onwards and then parse.
    """
    if "Total" not in line:
        return

    # cut off any rubbish before 'Total'
    idx = line.index("Total")
    sub = line[idx:].strip()

    parts = sub.split()
    parse_total(parts, ship_version_id, side, cur)


# ---------- TRIM & GM BLOCKS ----------


def slice_trim_block(text: str, block_title: str) -> str:
    """
    Strict slicing of one of the three blocks:
      - 'Light service draft'
      - 'Partial subdivision draft'
      - 'Deepest subdivision draft'

    We take from this title up to the next title (or end).
    """
    start = text.find(block_title)
    if start == -1:
        return ""

    titles = [
        "Light service draft",
        "Partial subdivision draft",
        "Deepest subdivision draft",
        "Details of choices and options",
        "Subdivision length",
    ]

    candidates = []
    for t in titles:
        if t == block_title:
            continue
        idx = text.find(t, start + 1)
        if idx != -1:
            candidates.append(idx)

    end = min(candidates) if candidates else len(text)
    return text[start:end]


def parse_trim_gm_block(text, block_title, condition_name, ship_version_id, cur):
    """
    Extract one of the three trim/GM conditions and insert into trim_gm.
    """
    block = slice_trim_block(text, block_title)
    if not block:
        return

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


# ---------- CONCLUSION ----------


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


# ---------- RTF → TEXT ----------


def rtf_to_text(raw: str) -> str:
    """
    Very small RTF → text converter tailored to your PIAS output.

    It keeps the content, tabs and newlines, and removes RTF control words.
    """
    s = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Map some controls to something useful
    s = s.replace(r"\tab", "\t")
    s = s.replace(r"\cell", " ")
    s = s.replace(r"\row", "\n")
    s = s.replace(r"\par", "\n")

    # Drop escaped characters \'hh
    s = re.sub(r"\\'[0-9a-fA-F]{2}", "", s)

    # Drop most remaining control words like \b, \fs22, etc.
    s = re.sub(r"\\[a-zA-Z]+\d* ?", "", s)

    # Remove braces
    s = s.replace("{", "").replace("}", "")

    return s


# ---------- MAIN IMPORT ----------


def import_probdam_rtf(
    rtf_path,
    ship_name=None,
    design_name=None,
    version=None,
    subversion=None,
    ship_run="",
):
    """
    Read one ProbDam .rtf output and fill:

      - probdam_case
      - probdam_total
      - trim_gm
      - probdam_conclusion
    """
    rtf_path = Path(rtf_path)
    if ship_name is None:
        ship_name, design_name, version, subversion = parse_filename(rtf_path)
        ship_run = ""

    conn = get_conn()
    try:
        ship_id = get_ship(conn, ship_name)
        ship_version_id = get_version(
            conn, ship_id, design_name, version, subversion, ship_run
        )

        with open(rtf_path, "r", encoding="latin-1", errors="ignore") as f:
            raw = f.read()

        text = rtf_to_text(raw)
        side = detect_side(text)

        with conn.cursor() as cur:
            # --- damage cases + totals ---
            for raw_line in text.splitlines():
                line = (raw_line or "").strip()
                if not line:
                    continue

                if "Damage case" in line or "boundary" in line:
                    continue

                # totals row (now robust)
                if "Total" in line:
                    parse_total_line(line, ship_version_id, side, cur)
                    continue

                # damage case rows
                parse_damage_line(line, ship_version_id, side, cur)

            # --- trim & GM, three conditions ---
            parse_trim_gm_block(
                text, "Light service draft", "light", ship_version_id, cur
            )
            parse_trim_gm_block(
                text, "Partial subdivision draft", "partial", ship_version_id, cur
            )
            parse_trim_gm_block(
                text, "Deepest subdivision draft", "deepest", ship_version_id, cur
            )

            # --- final conclusion ---
            parse_conclusion(text, ship_version_id, cur)

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parseProbdam.py <rtf_path>")
        sys.exit(1)

    import_probdam_rtf(sys.argv[1])
    print("Probdam RTF import completed.")
