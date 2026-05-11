import re
from pathlib import Path

from src.parsing.stability.parse_probdam_local import (
    get_local_conn,
    get_ship,
    get_version,
    parse_float,
    rtf_to_text,
    detect_side,
)

# Matches standard rows like:
# 1.1   0.0101  1.0000  0.0058  1.0000  0.0029  1.0000  0.0055
ROW_RE = re.compile(
    r"^\s*(?P<case>\d+\.\d+)\s+"
    r"(?P<pi_l>-?\d+(?:\.\d+)?)\s+(?P<si_l>-?\d+(?:\.\d+)?)\s+"
    r"(?P<pi_p>-?\d+(?:\.\d+)?)\s+(?P<si_p>-?\d+(?:\.\d+)?)\s+"
    r"(?P<pi_d>-?\d+(?:\.\d+)?)\s+(?P<si_d>-?\d+(?:\.\d+)?)\s+"
    r"(?P<ai>-?\d+(?:\.\d+)?)\s*$"
)


def _extract_conclusion(text: str):
    m_len = re.search(r"Subdivision length\s*=\s*([-\d\.]+)\s*m", text)
    m_r = re.search(r"Required subdivision index\s*R\s*=\s*([-\d\.]+)", text)
    m_a = re.search(r"Attained subdivision index\s*A\s*=\s*([-\d\.]+)", text)

    length = parse_float(m_len.group(1)) if m_len else None
    req_r = parse_float(m_r.group(1)) if m_r else None
    att_a = parse_float(m_a.group(1)) if m_a else None

    # In the sample: "The vessel does NOT comply ..." :contentReference[oaicite:11]{index=11}
    if re.search(r"does\s+NOT\s+comply", text, re.IGNORECASE):
        complies = False
    elif re.search(r"does\s+comply", text, re.IGNORECASE):
        complies = True
    else:
        complies = True  # default optimistic if line missing

    # Optional metadata shown in "Details of choices and options" :contentReference[oaicite:12]{index=12}
    m_step = re.search(
        r"Numerical integration step accuracy.*?:\s*(\d+)", text, re.IGNORECASE
    )
    step_accuracy = int(m_step.group(1)) if m_step else None

    penetration_reference = None
    m_ref = re.search(r"Reference point.*?:\s*(.+)", text, re.IGNORECASE)
    if m_ref:
        penetration_reference = m_ref.group(1).strip()

    return length, req_r, att_a, complies, step_accuracy, penetration_reference


def import_numint_rtf(
    rtf_path,
    ship_name=None,
    design_name=None,
    version=None,
    subversion=None,
    ship_run="",
):
    """
    Read one outputNumInt.rtf and fill:
      - numint_case
      - numint_conclusion
    """
    rtf_path = Path(rtf_path)

    if ship_name is None:
        raise ValueError(
            "import_numint_rtf requires explicit ship_name/design_name/version/subversion (same as runInvoke usage)."
        )

    with open(rtf_path, "r", encoding="latin-1", errors="ignore") as f:
        raw = f.read()

    text = rtf_to_text(raw)
    side = detect_side(text)  # "Damage at PS." :contentReference[oaicite:13]{index=13}

    # --- parse case rows ---
    cases = []

    for raw_line in text.splitlines():
        line = (raw_line or "").strip()
        if not line:
            continue

        # special first line: "Zero-compartment damages ..." :contentReference[oaicite:14]{index=14}
        if line.lower().startswith("zero-compartment damages"):
            parts = line.split()
            nums = [p for p in parts if re.fullmatch(r"-?\d+(?:\.\d+)?", p)]
            if len(nums) >= 7:
                cases.append(
                    (
                        "zero",
                        parse_float(nums[0]),
                        parse_float(nums[1]),
                        parse_float(nums[2]),
                        parse_float(nums[3]),
                        parse_float(nums[4]),
                        parse_float(nums[5]),
                        parse_float(nums[6]),
                    )
                )
            continue

        # ignore header / totals
        if (
            line.startswith("Damage case")
            or "Tlight" in line
            or "Not-included probabilities" in line
        ):
            continue
        if line.startswith("Total"):
            continue

        m = ROW_RE.match(line)
        if not m:
            continue

        cases.append(
            (
                m.group("case"),
                parse_float(m.group("pi_l")),
                parse_float(m.group("si_l")),
                parse_float(m.group("pi_p")),
                parse_float(m.group("si_p")),
                parse_float(m.group("pi_d")),
                parse_float(m.group("si_d")),
                parse_float(m.group("ai")),
            )
        )

    # --- parse conclusion / metadata ---
    length, req_r, att_a, complies, step_accuracy, penetration_reference = (
        _extract_conclusion(text)
    )

    conn = get_local_conn()
    try:
        ship_id = get_ship(conn, ship_name)
        ship_version_id = get_version(
            conn, ship_id, design_name, version, subversion, ship_run
        )

        with conn.cursor() as cur:
            # wipe previous import for idempotent reruns
            cur.execute(
                "DELETE FROM numint_case WHERE ship_version_id = %s", (ship_version_id,)
            )
            cur.execute(
                "DELETE FROM numint_conclusion WHERE ship_version_id = %s",
                (ship_version_id,),
            )

            if cases:
                cur.executemany(
                    """
                    INSERT INTO numint_case (
                      ship_version_id, side, damage_case,
                      pi_tlight, si_tlight,
                      pi_tpartial, si_tpartial,
                      pi_tdeepest, si_tdeepest,
                      ai
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            ship_version_id,
                            side,
                            damage_case,
                            pi_l,
                            si_l,
                            pi_p,
                            si_p,
                            pi_d,
                            si_d,
                            ai,
                        )
                        for (
                            damage_case,
                            pi_l,
                            si_l,
                            pi_p,
                            si_p,
                            pi_d,
                            si_d,
                            ai,
                        ) in cases
                    ],
                )

            cur.execute(
                """
                INSERT INTO numint_conclusion (
                  ship_version_id, side,
                  subdivision_length, required_index, attained_index, complies,
                  step_accuracy, penetration_reference
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    ship_version_id,
                    side,
                    length,
                    req_r,
                    att_a,
                    complies,
                    step_accuracy,
                    penetration_reference,
                ),
            )

        conn.commit()
        print(f"         -> NumInt imported: {len(cases)} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    print("This parser is meant to be called from runInvoke.py with ship/version info.")
    if len(sys.argv) == 2:
        print(
            "If you REALLY want to run standalone, wire filename->ship_version parsing like parseProbdam does."
        )
