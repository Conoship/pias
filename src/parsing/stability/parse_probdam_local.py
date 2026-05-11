"""
parseProbdamLocal.py
====================
SQLite mirror of parseProbdam.py for local testing before pushing to PostgreSQL.

Parses a PIAS probdam .rtf output file and populates:
  - trim_gm
  - probdam_case
  - probdam_total
  - probdam_conclusion

Usage (standalone):
    python parseProbdamLocal.py <path/to/ship_design_ver_sub_probdam.rtf>

The filename convention is the same as parseProbdam.py:
    <ship>_<design>_<version>_<subversion>_probdam.rtf
"""

import re
import sqlite3
from pathlib import Path

from src.db.db import get_local_conn, create_all_tables

# ---------- FILENAME PARSING ----------


def parse_filename(path: str):
    """
    Expect names like:
      <ship>_<design>_<version>_<subversion>_probdam.rtf
    Extra parts after the 4th segment are joined as subversion.
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


def get_ship(conn: sqlite3.Connection, ship_name: str) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM ship WHERE name = ?", (ship_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO ship (name) VALUES (?)", (ship_name,))
    conn.commit()
    return cur.lastrowid


def get_version(
    conn: sqlite3.Connection,
    ship_id: int,
    design_name: str,
    version: str,
    subversion: str,
    ship_run: str = "",
) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id FROM ship_version
        WHERE ship_id = ?
          AND design_name = ?
          AND version = ?
          AND subversion = ?
          AND ship_run = ?
        """,
        (ship_id, design_name, version, subversion, ship_run),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO ship_version (ship_id, design_name, version, subversion, ship_run)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ship_id, design_name, version, subversion, ship_run),
    )
    conn.commit()
    return cur.lastrowid


# ---------- RTF → TEXT ----------


def rtf_to_text(raw: str) -> str:
    """
    Minimal RTF → plain-text converter (same logic as parseProbdam.py).
    Keeps content, tabs and newlines; strips RTF control words.
    """
    s = raw.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace(r"\tab", "\t")
    s = s.replace(r"\cell", " ")
    s = s.replace(r"\row", "\n")
    s = s.replace(r"\par", "\n")
    s = re.sub(r"\\'[0-9a-fA-F]{2}", "", s)
    s = re.sub(r"\\[a-zA-Z]+\d* ?", "", s)
    s = s.replace("{", "").replace("}", "")
    return s


# ---------- TEXT PARSING HELPERS ----------


def detect_side(text: str):
    m = re.search(r"Damage at\s+([A-Z]+)", text)
    return m.group(1) if m else None


def _find_float(pattern: str, text: str):
    m = re.search(pattern, text)
    return parse_float(m.group(1)) if m else None


# ---------- DAMAGE CASES ----------


def parse_damage_line(line: str, ship_version_id: int, side, cur: sqlite3.Cursor):
    line = (line or "").strip()
    if not line:
        return
    parts = line.split()
    if not parts or not re.match(r"^\d+\.\d+$", parts[0]):
        return

    # Pad/trim to exactly 12 columns (same as parseProbdam.py)
    while len(parts) < 12:
        parts.append(None)
    parts = parts[:12]

    cur.execute(
        """
        INSERT INTO probdam_case (
            ship_version_id, side, damage_case,
            aft_boundary, fwd_boundary, inside_boundary, upper_boundary,
            pi_tlight, si_tlight,
            pi_tpartial, si_tpartial,
            pi_tdeepest, si_tdeepest,
            ai
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            ship_version_id,
            side,
            parts[0],
            parse_float(parts[1]),
            parse_float(parts[2]),
            parse_float(parts[3]),
            parse_float(parts[4]),
            parse_float(parts[5]),
            parse_float(parts[6]),
            parse_float(parts[7]),
            parse_float(parts[8]),
            parse_float(parts[9]),
            parse_float(parts[10]),
            parse_float(parts[11]),
        ),
    )


def parse_total_line(line: str, ship_version_id: int, side, cur: sqlite3.Cursor):
    """
    The 'Total' line can have RTF noise before it; cut from 'Total' onwards.
    """
    if "Total" not in line:
        return
    sub = line[line.index("Total") :].strip()
    parts = sub.split()
    if not parts or not parts[0].startswith("Total"):
        return

    nums = [parse_float(c) for c in parts[1:] if c is not None]
    while len(nums) < 4:
        nums.append(None)

    cur.execute(
        """
        INSERT INTO probdam_total (
            ship_version_id, side,
            total_pi_tlight, total_pi_tpartial, total_pi_tdeepest, total_ai
        ) VALUES (?,?,?,?,?,?)
        """,
        (ship_version_id, side, nums[0], nums[1], nums[2], nums[3]),
    )


# ---------- TRIM & GM BLOCKS ----------


def slice_trim_block(text: str, block_title: str) -> str:
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
    candidates = [
        text.find(t, start + 1)
        for t in titles
        if t != block_title and text.find(t, start + 1) != -1
    ]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def parse_trim_gm_block(
    text: str,
    block_title: str,
    condition_name: str,
    ship_version_id: int,
    cur: sqlite3.Cursor,
):
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
            ship_version_id, condition_name,
            draft, trim, vcg, mg, displacement,
            attained_index, required_index
        )
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT (ship_version_id, condition_name) DO UPDATE SET
            draft = excluded.draft,
            trim = excluded.trim,
            vcg = excluded.vcg,
            mg = excluded.mg,
            displacement = excluded.displacement,
            attained_index = excluded.attained_index,
            required_index = excluded.required_index
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


def parse_conclusion(text: str, ship_version_id: int, cur: sqlite3.Cursor):
    m_len = re.search(r"Subdivision length\s*=\s*([-\d\.]+)\s*m", text)
    m_r = re.search(r"Required subdivision index R\s*=\s*([-\d\.]+)", text)
    m_a = re.search(r"Attained subdivision index A\s*=\s*([-\d\.]+)", text)

    if not (m_len and m_r and m_a):
        print("  [warning] Could not find conclusion block in RTF.")
        return

    length = parse_float(m_len.group(1))
    req_r = parse_float(m_r.group(1))
    att_a = parse_float(m_a.group(1))
    complies = 0 if "does NOT comply" in text else 1

    cur.execute(
        """
        INSERT INTO probdam_conclusion (
            ship_version_id,
            subdivision_length, required_index, attained_index, complies
        ) VALUES (?,?,?,?,?)
        """,
        (ship_version_id, length, req_r, att_a, complies),
    )


# ---------- MAIN IMPORT ----------


def import_probdam_rtf_local(
    rtf_path,
    ship_name: str | None = None,
    design_name: str | None = None,
    version: str | None = None,
    subversion: str | None = None,
    ship_run: str = "",
):
    """
    Read one ProbDam .rtf output and populate the local SQLite database with:
      - trim_gm          (draft / trim / VCG / MG / displacement per condition)
      - probdam_case     (one row per damage case)
      - probdam_total    (totals row)
      - probdam_conclusion (subdivision length, R, A, complies)

    Args:
        rtf_path:   Path to the .rtf file.
        ship_name, design_name, version, subversion, ship_run:
            If None, these are inferred from the filename (same convention as
            parseProbdam.py).  Supply them explicitly when called from
            runInvoke.py / a batch script so the identifiers match the layout
            import exactly.
    """
    rtf_path = Path(rtf_path)

    if ship_name is None:
        ship_name, design_name, version, subversion = parse_filename(rtf_path)
        ship_run = ""

    with open(rtf_path, "r", encoding="latin-1", errors="ignore") as f:
        raw = f.read()

    text = rtf_to_text(raw)
    side = detect_side(text)

    conn = get_local_conn()
    create_all_tables(conn)  # idempotent – safe to call every time

    try:
        ship_id = get_ship(conn, ship_name)
        ship_version_id = get_version(
            conn, ship_id, design_name, version, subversion, ship_run
        )

        cur = conn.cursor()

        # Wipe previous import for this ship_version so reruns are idempotent.
        cur.execute(
            "DELETE FROM probdam_case WHERE ship_version_id = ?", (ship_version_id,)
        )
        cur.execute(
            "DELETE FROM probdam_total WHERE ship_version_id = ?", (ship_version_id,)
        )
        cur.execute(
            "DELETE FROM probdam_conclusion WHERE ship_version_id = ?",
            (ship_version_id,),
        )
        # trim_gm uses ON CONFLICT DO UPDATE so no explicit delete needed.

        # --- damage cases + totals ---
        for raw_line in text.splitlines():
            line = (raw_line or "").strip()
            if not line:
                continue
            if "Damage case" in line or "boundary" in line:
                continue
            if "Total" in line:
                parse_total_line(line, ship_version_id, side, cur)
                continue
            parse_damage_line(line, ship_version_id, side, cur)

        # --- trim & GM blocks ---
        parse_trim_gm_block(text, "Light service draft", "light", ship_version_id, cur)
        parse_trim_gm_block(
            text, "Partial subdivision draft", "partial", ship_version_id, cur
        )
        parse_trim_gm_block(
            text, "Deepest subdivision draft", "deepest", ship_version_id, cur
        )

        # --- conclusion ---
        parse_conclusion(text, ship_version_id, cur)

        conn.commit()
        print(
            f"  -> Probdam local import complete for ship_version_id={ship_version_id}"
        )

        # Quick sanity print so you can eyeball the result immediately.
        _print_summary(conn, ship_version_id)

    finally:
        conn.close()


def _print_summary(conn: sqlite3.Connection, ship_version_id: int):
    """Print a brief summary to the terminal for quick verification."""
    cur = conn.cursor()

    cur.execute(
        "SELECT condition_name, draft, displacement, attained_index, required_index "
        "FROM trim_gm WHERE ship_version_id = ? ORDER BY condition_name",
        (ship_version_id,),
    )
    rows = cur.fetchall()
    print("\n  trim_gm rows:")
    for r in rows:
        print(
            f"    condition={r[0]:10s}  draft={r[1]}  disp={r[2]}  "
            f"A={r[3]}  R={r[4]}"
        )

    cur.execute(
        "SELECT COUNT(*) FROM probdam_case WHERE ship_version_id = ?",
        (ship_version_id,),
    )
    print(f"  probdam_case rows : {cur.fetchone()[0]}")

    cur.execute(
        "SELECT subdivision_length, required_index, attained_index, complies "
        "FROM probdam_conclusion WHERE ship_version_id = ?",
        (ship_version_id,),
    )
    row = cur.fetchone()
    if row:
        status = "COMPLIES" if row[3] else "DOES NOT COMPLY"
        print(f"  conclusion        : L={row[0]} m  R={row[1]}  A={row[2]}  {status}")
    print()


# ---------- STANDALONE ----------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parseProbdamLocal.py <path/to/_probdam.rtf>")
        print(
            "       (filename must follow the <ship>_<design>_<ver>_<sub>_probdam.rtf convention)"
        )
        sys.exit(1)

    import_probdam_rtf_local(sys.argv[1])
    print("Probdam local import completed.")
