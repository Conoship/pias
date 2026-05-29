# Import third party packages.
import numpy as np
import pandas as pd


def cross_section_area(section_points: pd.DataFrame) -> float:
    """
    Calculate area of one cross-section using B-H points.
    """
    points = section_points[["B", "H"]].dropna().drop_duplicates().to_numpy()

    if len(points) < 3:
        return 0.0

    center = points.mean(axis=0)

    # Sort points around the centre so polygon area works.
    angles = np.arctan2(
        points[:, 1] - center[1],
        points[:, 0] - center[0],
    )

    points = points[np.argsort(angles)]

    b = points[:, 0]
    h = points[:, 1]

    area = 0.5 * abs(
        np.dot(b, np.roll(h, -1)) - np.dot(h, np.roll(b, -1))
    )

    return float(area)


def calculate_subcompartment_volume(sub_points: pd.DataFrame) -> float:
    """
    Calculate one subcompartment volume.

    1. Group points by L station.
    2. Calculate B-H area at each L.
    3. Integrate areas along L.
    """
    sub_points = sub_points.copy()
    sub_points["L_round"] = sub_points["L"].round(6)

    areas = []

    for L_value, section in sub_points.groupby("L_round"):
        area = cross_section_area(section)

        areas.append(
            {
                "L": L_value,
                "area": area,
            }
        )

    areas_df = pd.DataFrame(areas).sort_values("L")

    if len(areas_df) < 2:
        return 0.0

    volume = np.trapezoid(
        areas_df["area"],
        areas_df["L"],
    )

    return float(abs(volume))


def fill_missing_breadth(points: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing B as the outside shell boundary.

    Assumptions:
    - B = 0 is centreline.
    - B can be positive or negative.
    - NULL B means outside shell.
    - Outside shell is approximated as +/- breadth / 2.
    """
    points = points.copy()

    missing_b = points["B"].isna()
    half_breadth = pd.to_numeric(points["half_breadth"], errors="coerce")

    group_cols = [
        "ship_version_id",
        "compartment_id",
        "subcompartment_id",
    ]

    def infer_shell_sign(known_b: pd.Series) -> float:
        known_b = known_b.dropna()

        if known_b.empty:
            return np.nan

        shell_b = known_b.loc[known_b.abs().idxmax()]

        if shell_b == 0:
            return np.nan

        return float(np.sign(shell_b))

    inferred_sign = points.groupby(group_cols)["B"].transform(infer_shell_sign)

    side_sign = np.select(
        [
            points["side"].eq("ps_only"),
            points["side"].eq("sb_only"),
        ],
        [
            -1.0,
            1.0,
        ],
        default=np.nan,
    )

    final_sign = np.where(
        np.isnan(side_sign),
        inferred_sign,
        side_sign,
    )

    final_sign = pd.Series(final_sign, index=points.index).fillna(1.0)
    points.loc[missing_b, "B"] = final_sign[missing_b] * half_breadth[missing_b]

    return points


def fill_missing_length(points: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing L at the longitudinal end points.

    Assumptions:
    - NULL L on forward/front points means the forward perpendicular.
    - If LPP is missing, the known forward layout end is used.
    - NULL L on aft points means the aft fallback station at -3.
    - NULL L on midship points means the full cargo-hold span.
    """
    points = points.copy()

    missing_l = points["L"].isna()
    aftfwd = points["aftfwd_and_num"].fillna("").astype(str).str.lower()
    lpp = pd.to_numeric(points["lpp"], errors="coerce")
    ship_max_l = pd.to_numeric(points["ship_max_l"], errors="coerce")
    cargo_min_l = pd.to_numeric(points["cargo_min_l"], errors="coerce")
    cargo_max_l = pd.to_numeric(points["cargo_max_l"], errors="coerce")

    forward_point = aftfwd.str.contains("fwd|fore|front", regex=True)
    aft_point = aftfwd.str.contains("aft", regex=False)
    midship_point = aftfwd.str.contains("mid|middle", regex=True)

    forward_l = lpp.fillna(ship_max_l)
    points.loc[missing_l & forward_point, "L"] = forward_l[
        missing_l & forward_point
    ]
    points.loc[missing_l & aft_point, "L"] = -3.0

    midship_rows = points[missing_l & midship_point]
    if not midship_rows.empty:
        cargo_start = midship_rows.copy()
        cargo_end = midship_rows.copy()

        cargo_start["L"] = cargo_min_l.loc[midship_rows.index]
        cargo_end["L"] = cargo_max_l.loc[midship_rows.index]

        points = points.drop(index=midship_rows.index)
        points = pd.concat([points, cargo_start, cargo_end], ignore_index=True)

    return points


def fill_missing_height(points: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing H from the frustum point vertical position.

    Assumptions:
    - Aft/Fwd 1 and 2 are bottom points.
    - Aft/Fwd 3 and 4 are top points.
    - Missing bottom H is 0.
    - Missing top H is depth in midship and depth + 1 at aft/fwd ends.
    """
    points = points.copy()

    missing_h = points["H"].isna()
    aftfwd = points["aftfwd_and_num"].fillna("").astype(str).str.lower()
    depth = pd.to_numeric(points["depth"], errors="coerce")

    bottom_point = aftfwd.str.contains(r"[12]\s*$", regex=True)
    top_point = aftfwd.str.contains(r"[34]\s*$", regex=True)
    end_point = aftfwd.str.contains("aft|fwd|fore|front", regex=True)

    top_height = np.where(end_point, depth + 1.0, depth)
    top_height = pd.Series(top_height, index=points.index)

    points.loc[missing_h & bottom_point, "H"] = 0.0
    points.loc[missing_h & top_point, "H"] = top_height[missing_h & top_point]

    return points


def derive_compartment_volume_by_type(conn: object) -> pd.DataFrame:
    """
    Derive compartment volume per type for each ship_version_id.
    """

    #  Load geometry points from database
    points = pd.read_sql_query(
        """
        WITH geometry_bounds AS (
            SELECT
                comp.ship_version_id,
                MIN(CASE
                    WHEN comp.design_content_id_number IN (1, 12)
                    THEN fp.L
                END) AS cargo_min_l,
                MAX(CASE
                    WHEN comp.design_content_id_number IN (1, 12)
                    THEN fp.L
                END) AS cargo_max_l,
                MAX(fp.L) AS ship_max_l

            FROM compartment comp

            JOIN subcompartment sub
                ON sub.compartment_id = comp.id

            JOIN subcompartment_shape ss
                ON ss.shape_guid = sub.shape_guid
               AND ss.ship_version_id = comp.ship_version_id

            JOIN frustum_point fp
                ON fp.subcompartment_shape_id = ss.id

            WHERE fp.L IS NOT NULL

            GROUP BY comp.ship_version_id
        )

        SELECT
            comp.ship_version_id,
            comp.id AS compartment_id,
            comp.design_content_id_number AS content_id,

            sub.id AS subcompartment_id,
            COALESCE(sub.sign, 1) AS sign,
            ss.side,

            md.breadth / 2.0 AS half_breadth,
            md.depth,
            md.lpp,
            gb.cargo_min_l,
            gb.cargo_max_l,
            gb.ship_max_l,

            fp.aftfwd_and_num,
            fp.L,
            fp.B,
            fp.H

        FROM compartment comp

        JOIN subcompartment sub
            ON sub.compartment_id = comp.id

        JOIN subcompartment_shape ss
            ON ss.shape_guid = sub.shape_guid
           AND ss.ship_version_id = comp.ship_version_id

        JOIN frustum_point fp
            ON fp.subcompartment_shape_id = ss.id

        LEFT JOIN main_dimensions md
            ON md.ship_version_id = comp.ship_version_id

        LEFT JOIN geometry_bounds gb
            ON gb.ship_version_id = comp.ship_version_id
        """,
        conn,
    )

    if points.empty:
        return pd.DataFrame(columns=["ship_version_id"])

    points = fill_missing_length(points)
    points = points.dropna(subset=["L"])

    if points.empty:
        return pd.DataFrame(columns=["ship_version_id"])

    points = fill_missing_breadth(points)
    points = fill_missing_height(points)

    #  Calculate volume for each subcompartment
    subcompartment_rows = []

    group_cols = [
        "ship_version_id",
        "compartment_id",
        "content_id",
        "subcompartment_id",
        "sign",
    ]

    for keys, group in points.groupby(group_cols, dropna=False):
        ship_version_id, compartment_id, content_id, sub_id, sign = keys

        volume = calculate_subcompartment_volume(group)

        signed_volume = volume * float(sign)

        subcompartment_rows.append(
            {
                "ship_version_id": ship_version_id,
                "compartment_id": compartment_id,
                "content_id": content_id,
                "subcompartment_volume": signed_volume,
            }
        )

    sub_df = pd.DataFrame(subcompartment_rows)

    #  Sum subcompartment volumes into compartment volumes
    comp_df = (
        sub_df
        .groupby(
            ["ship_version_id", "compartment_id", "content_id"],
            as_index=False,
        )
        .agg(
            compartment_volume=("subcompartment_volume", "sum")
        )
    )

    comp_df["compartment_volume"] = comp_df["compartment_volume"].clip(lower=0)

    #  Sum compartment volumes by type
    ship_ids = sorted(comp_df["ship_version_id"].unique())

    output = pd.DataFrame(
        {
            "ship_version_id": ship_ids,
        }
    )

    content_types = {
        1: "cargo",
        2: "fuel_oil",
        3: "gas_oil",
        4: "potable_water",
        6: "ballast",
        8: "void",
        12: "cargohold_hatch",
    }

    for content_id, content_name in content_types.items():
        type_volume = (
            comp_df[comp_df["content_id"] == content_id]
            .groupby("ship_version_id")["compartment_volume"]
            .sum()
            .reset_index()
        )

        type_volume = type_volume.rename(
            columns={
                "compartment_volume": f"{content_name}_volume_total"
            }
        )

        output = output.merge(
            type_volume,
            on="ship_version_id",
            how="left",
        )

    # Replace missing type volumes with zero (check if needed)
    volume_total_cols = [
        col for col in output.columns
        if col.endswith("_volume_total")
    ]

    output[volume_total_cols] = output[volume_total_cols].fillna(0.0)

    #  Total volume and volume ratios
    output["total_compartment_volume"] = output[volume_total_cols].sum(axis=1)

    for col in volume_total_cols:
        base_name = col.replace("_volume_total", "")

        output[f"{base_name}_volume_ratio"] = np.where(
            output["total_compartment_volume"] > 0,
            output[col] / output["total_compartment_volume"],
            0.0,
        )

    return output
