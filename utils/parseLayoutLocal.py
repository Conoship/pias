import sys
import sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET

from db import get_local_conn, create_layout_tables


def parse_filename(path):
    """Extract ship, design, version and subversion from the filename."""
    name = Path(path).name
    stem = name
    if stem.endswith(".fromLayout.xml"):
        stem = stem[: -len(".fromLayout.xml")]
    else:
        stem = Path(path).stem

    parts = stem.split("_")

    ship = parts[0] if len(parts) > 0 else "unknownship"
    design = parts[1] if len(parts) > 1 else "unknowndesign"
    version = parts[2] if len(parts) > 2 else "unknownversion"
    subversion = parts[3] if len(parts) > 3 else ""
    ship_run = "_".join(parts[4:]) if len(parts) > 4 else ""

    return (
        ship.strip(),
        design.strip(),
        version.strip(),
        subversion.strip(),
        ship_run.strip(),
    )


def parse_float(text):
    if text is None:
        return None
    t = text.strip()
    if t.upper() in ("INF", "-INF"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def parse_int(text):
    if text is None:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


def load_xml(xml_path):
    tree = ET.parse(xml_path)
    return tree.getroot()


def get_ship(conn: sqlite3.Connection, ship_name):
    """Get ship.id for name, creating it if needed."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM ship WHERE name = ?", (ship_name,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("INSERT INTO ship (name) VALUES (?)", (ship_name,))
    conn.commit()
    return cur.lastrowid


def get_version(
    conn: sqlite3.Connection, ship_id, design_name, version, subversion, ship_run
):
    """Get ship_version.id for given ship & identifiers, creating if needed."""
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


def import_content_categories(conn: sqlite3.Connection, root):
    """Fill content_category table from XML Content_category blocks."""
    cur = conn.cursor()
    for cc in root.findall(".//Content_categories/Content_category"):
        design_content_id = parse_int(cc.findtext("Design_content_IDnumber"))
        name = cc.findtext("Name")
        if design_content_id is None or not name:
            continue
        cur.execute(
            """
            INSERT OR IGNORE INTO content_category (design_content_id_number, name)
            VALUES (?, ?)
            """,
            (design_content_id, name),
        )
    conn.commit()


def import_coordinates(conn: sqlite3.Connection, root, ship_version_id):
    """
    Import subcompartment_shape and frustum_point rows.
    Also compute approximate breadth/height span per shape_guid for pipe detection.
    """
    shape_guid_spans = {}

    cur = conn.cursor()
    for shape in root.findall(".//Subcompartment_shapes/Subcompartment_shape"):
        shape_guid = shape.findtext("Subcompartment_shape_GUID")
        if not shape_guid:
            continue

        side = shape.findtext("Side")
        shape_type = shape.findtext("Subcompartment_shape_type")

        cur.execute(
            """
            INSERT INTO subcompartment_shape (ship_version_id, shape_guid, side)
            VALUES (?, ?, ?)
            """,
            (ship_version_id, shape_guid, side),
        )
        shape_id = cur.lastrowid

        span_b = None
        span_h = None

        if shape_type == "shapetype_frustum":
            bs = []
            hs = []
            for fp in shape.findall(".//Frustum_points/Frustum_point"):
                aft_fwd_number = fp.findtext("AftFwd_and_number")
                ref = fp.find("Reference_vector")
                if ref is None:
                    continue

                l = parse_float(ref.findtext("L/Reference_value/Distance"))
                b = parse_float(ref.findtext("B/Reference_value/Distance"))
                h = parse_float(ref.findtext("H/Reference_value/Distance"))

                if b is not None:
                    bs.append(b)
                if h is not None:
                    hs.append(h)

                cur.execute(
                    """
                    INSERT INTO frustum_point
                        (subcompartment_shape_id, aftfwd_and_num, L, B, H)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (shape_id, aft_fwd_number, l, b, h),
                )

            if len(bs) >= 2:
                span_b = max(bs) - min(bs)
            if len(hs) >= 2:
                span_h = max(hs) - min(hs)

        shape_guid_spans[shape_guid] = (span_b, span_h)

    conn.commit()
    return shape_guid_spans


def import_compartments(
    conn: sqlite3.Connection, root, ship_version_id, shape_guid_spans
):
    """
    Import compartment and subcompartment rows, including pipe detection.
    """
    cur = conn.cursor()
    for comp in root.findall(".//Compartment"):
        selected = (
            comp.findtext("Selected_for_output_and_calculations") or ""
        ).strip().lower() == "true"
        if not selected:
            continue

        xml_comp_id = parse_int(comp.findtext("Compartment_ID"))
        xml_guid = comp.findtext("Compartment_GUID")
        name = comp.findtext("Name") or ""
        design_content_id = parse_int(comp.findtext("Design_content_IDnumber"))

        cur.execute(
            """
            INSERT INTO compartment
                (ship_version_id,
                    xml_comparment_id,
                    xml_compartment_guid,
                    name,
                    selected_for_output,
                    design_content_id_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ship_version_id,
                xml_comp_id,
                xml_guid,
                name,
                int(selected),
                design_content_id,
            ),
        )
        compartment_id = cur.lastrowid

        name_lower = name.lower()
        contains_pipe = "pipe" in name_lower
        contains_pipeduct = "pipeduct" in name_lower or "pipe duct" in name_lower

        for subcomp in comp.findall(".//Subcompartments/Subcompartment"):
            shape_guid = subcomp.findtext("Shape_GUID")
            subcomp_guid = subcomp.findtext("Subcompartment_GUID")
            sign = parse_int(subcomp.findtext("Sign"))
            perm_ds = parse_float(subcomp.findtext("Permeability_for_damage_stability"))

            span_b, span_h = shape_guid_spans.get(shape_guid, (None, None))
            small_b = span_b is not None and span_b < 0.3
            small_h = span_h is not None and span_h < 0.3

            is_pipe = int(
                bool(contains_pipe and not contains_pipeduct and (small_b or small_h))
            )

            cur.execute(
                """
                INSERT INTO subcompartment
                    (compartment_id,
                        shape_guid,
                        subcompartment_guid,
                        sign,
                        permeability_for_damage_stability,
                        is_pipe)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    compartment_id,
                    shape_guid,
                    subcomp_guid,
                    sign,
                    perm_ds,
                    is_pipe,
                ),
            )

        for point in comp.findall(".//Special_points/Point"):
            point_name = point.findtext("Name") or ""
            opening_type = point.findtext("Type_of_point") or ""

            ref = point.find("Reference_vector")
            if ref is not None:
                l = parse_float(ref.findtext("L/Reference_value/Distance"))
                b = parse_float(ref.findtext("B/Reference_value/Distance"))
                h = parse_float(ref.findtext("H/Reference_value/Distance"))
            else:
                l = b = h = None

            cur.execute(
                """
                INSERT INTO opening
                    (ship_version_id,
                    compartment_id,
                    description,
                    opening_type,
                    L, B, H)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ship_version_id,
                    compartment_id,
                    point_name,
                    opening_type,
                    l,
                    b,
                    h,
                ),
            )

    conn.commit()


def import_layout_xml(xml_path):
    xml_path = Path(xml_path)
    ship_name, design_name, version, subversion, ship_run = parse_filename(xml_path)

    root = load_xml(xml_path)
    print("root tag:",root.tag)
    print("first 50")
    for i,elem in enumerate(root.iter()):
        print(i,elem.tag)
        if i >= 49:
            break
    print("Root tag:", root.tag)

    print("Content categories found:",
        len(root.findall(".//Content_categories/Content_category")))

    print("Subcompartment shapes found:",
        len(root.findall(".//Subcompartment_shapes/Subcompartment_shape")))

    print("Compartments found:",
        len(root.findall(".//Compartment")))

    print("Selected compartments found:",
        sum(
            1 for comp in root.findall(".//Compartment")
            if (comp.findtext("Selected_for_output_and_calculations") or "").strip().lower() == "true"
        ))
    conn = get_local_conn()
    create_layout_tables(conn)
    try:
        ship_id = get_ship(conn, ship_name)
        ship_version_id = get_version(
            conn, ship_id, design_name, version, subversion, ship_run
        )
        import_content_categories(conn, root)
        shape_guid_spans = import_coordinates(conn, root, ship_version_id)
        import_compartments(conn, root, ship_version_id, shape_guid_spans)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parseLayoutLocal.py <xml_path>")
        sys.exit(1)

    xml_path = sys.argv[1]
    import_layout_xml(xml_path)
    print("Layout import completed.")
