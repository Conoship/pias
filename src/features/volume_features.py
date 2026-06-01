import numpy as np
import pandas as pd


CONTENT_TYPES = {
    1: "cargo",
    2: "fuel_oil",
    3: "gas_oil",
    4: "potable_water",
    6: "ballast",
    8: "void",
    12: "cargohold_hatch",
}


def cross_section_area(section: pd.DataFrame) -> float:
    """
    Calculate the B-H polygon area for one L station.
    """
    points = section[["B", "H"]].dropna().drop_duplicates().to_numpy()

    if len(points) < 3:
        return 0.0

    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    points = points[np.argsort(angles)]

    b = points[:, 0]
    h = points[:, 1]

    area = 0.5 * abs(
        np.dot(b, np.roll(h, -1)) - np.dot(h, np.roll(b, -1))
    )

    return float(area)


def subcompartment_volume(points: pd.DataFrame) -> float:
    """
    Calculate one subcompartment volume by integrating section areas over L.
    """
    areas = []
    points = points.copy()
    points["L_round"] = points["L"].round(6)

    for l_value, section in points.groupby("L_round", sort=True):
        areas.append(
            {
                "L": float(l_value),
                "area": cross_section_area(section),
            }
        )

    if len(areas) < 2:
        return 0.0

    areas_df = pd.DataFrame(areas).sort_values("L")

    if hasattr(np, "trapezoid"):
        volume = np.trapezoid(areas_df["area"], areas_df["L"])
    else:
        volume = np.trapz(areas_df["area"], areas_df["L"])

    return float(abs(volume))


def fill_missing_length(points: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing L values.

    Assumptions:
    - Missing forward/front L is the forward perpendicular, using LPP when available.
    - If LPP is missing, use the largest known layout L value.
    - Missing aft L is set to -3.0.
    - Missing midship L represents the cargo area, so the row is copied to both
      cargo_min_l and cargo_max_l.
    """
    points = points.copy()

    missing_l = points["L"].isna()
    if not missing_l.any():
        return points

    aftfwd = points["aftfwd_and_num"].fillna("").astype(str).str.lower()
    lpp = pd.to_numeric(points["lpp"], errors="coerce")
    ship_max_l = pd.to_numeric(points["ship_max_l"], errors="coerce")
    cargo_min_l = pd.to_numeric(points["cargo_min_l"], errors="coerce")
    cargo_max_l = pd.to_numeric(points["cargo_max_l"], errors="coerce")

    forward_point = aftfwd.str.contains("fwd|fore|front", regex=True)
    aft_point = aftfwd.str.contains("aft", regex=False)
    midship_point = aftfwd.str.contains("mid|middle", regex=True)

    forward_l = lpp.fillna(ship_max_l)
    points.loc[missing_l & forward_point, "L"] = forward_l[missing_l & forward_point]
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


def fill_missing_breadth(points: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing B values.

    Assumptions:
    - B = 0 is the centreline.
    - Missing B means the point is on the outside shell.
    - The outside shell is approximated as +/- half_breadth.
    - The sign comes from the shape side when possible, otherwise from the
      largest known B value in the same subcompartment.
    """
    points = points.copy()

    missing_b = points["B"].isna()
    if not missing_b.any():
        return points

    group_cols = ["ship_version_id", "compartment_id", "subcompartment_id"]
    half_breadth = pd.to_numeric(points["half_breadth"], errors="coerce")

    def infer_sign(values: pd.Series) -> float:
        values = values.dropna()
        if values.empty:
            return np.nan

        outer_b = values.loc[values.abs().idxmax()]
        if outer_b == 0:
            return np.nan

        return float(np.sign(outer_b))

    inferred_sign = points.groupby(group_cols, sort=False)["B"].transform(infer_sign)

    side_sign = np.select(
        [points["side"].eq("ps_only"), points["side"].eq("sb_only")],
        [-1.0, 1.0],
        default=np.nan,
    )

    final_sign = np.where(np.isnan(side_sign), inferred_sign, side_sign)
    final_sign = pd.Series(final_sign, index=points.index).fillna(1.0)

    points.loc[missing_b, "B"] = final_sign[missing_b] * half_breadth[missing_b]

    return points


def fill_missing_height(points: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing H values.

    Assumptions:
    - Aft/Fwd points ending in 1 or 2 are bottom points.
    - Aft/Fwd points ending in 3 or 4 are top points.
    - Missing bottom H is 0.
    - Missing top H is depth, or depth + 1.0 at aft/fwd ends.
    """
    points = points.copy()

    missing_h = points["H"].isna()
    if not missing_h.any():
        return points

    aftfwd = points["aftfwd_and_num"].fillna("").astype(str).str.lower()
    depth = pd.to_numeric(points["depth"], errors="coerce")

    bottom_point = aftfwd.str.contains(r"[12]\s*$", regex=True)
    top_point = aftfwd.str.contains(r"[34]\s*$", regex=True)
    end_point = aftfwd.str.contains("aft|fwd|fore|front", regex=True)

    top_height = pd.Series(np.where(end_point, depth + 1.0, depth), index=points.index)

    points.loc[missing_h & bottom_point, "H"] = 0.0
    points.loc[missing_h & top_point, "H"] = top_height[missing_h & top_point]

    return points


def clean_points(points: pd.DataFrame) -> pd.DataFrame:
    points = fill_missing_length(points)
    points = points.dropna(subset=["L"])

    points = fill_missing_breadth(points)
    points = fill_missing_height(points)
    points = points.dropna(subset=["L", "B", "H"])

    return points


def read_points_for_ship_versions(
    conn: object,
    ship_version_ids: list[int],
) -> pd.DataFrame:
    """
    Read frustum points for a batch of ship versions.
    """
    if not ship_version_ids:
        return pd.DataFrame()

    content_ids = tuple(CONTENT_TYPES.keys())
    placeholders = ", ".join("?" for _ in content_ids)
    ship_placeholders = ", ".join("?" for _ in ship_version_ids)

    query = f"""
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
              AND comp.ship_version_id IN ({ship_placeholders})

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

        WHERE comp.ship_version_id IN ({ship_placeholders})
          AND comp.design_content_id_number IN ({placeholders})
    """

    params = (*ship_version_ids, *ship_version_ids, *content_ids)
    return pd.read_sql_query(query, conn, params=params)


def read_points_for_ship(conn: object, ship_version_id: int) -> pd.DataFrame:
    """
    Read frustum points for one ship version.
    """
    return read_points_for_ship_versions(conn, [ship_version_id])


def calculate_compartment_volumes(points: pd.DataFrame) -> pd.DataFrame:
    """
    Return one volume row per compartment.
    """
    group_cols = [
        "ship_version_id",
        "compartment_id",
        "content_id",
        "subcompartment_id",
        "sign",
    ]

    rows = []

    for keys, group in points.groupby(group_cols, sort=False, dropna=False):
        ship_version_id, compartment_id, content_id, _sub_id, sign = keys

        volume = subcompartment_volume(group)
        signed_volume = volume * float(sign if pd.notna(sign) else 1.0)

        rows.append(
            {
                "ship_version_id": ship_version_id,
                "compartment_id": compartment_id,
                "content_id": content_id,
                "subcompartment_volume": signed_volume,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "ship_version_id",
                "compartment_id",
                "content_id",
                "compartment_volume",
            ]
        )

    sub_df = pd.DataFrame(rows)
    comp_df = (
        sub_df
        .groupby(
            ["ship_version_id", "compartment_id", "content_id"],
            as_index=False,
            sort=False,
        )
        .agg(compartment_volume=("subcompartment_volume", "sum"))
    )

    comp_df["compartment_volume"] = comp_df["compartment_volume"].clip(lower=0.0)

    return comp_df


def aggregate_volume_features(comp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Turn compartment volumes into one feature row per ship version.
    """
    volume_cols = [f"{name}_volume_total" for name in CONTENT_TYPES.values()]
    ratio_cols = [f"{name}_volume_ratio" for name in CONTENT_TYPES.values()]
    count_cols = [f"{name}_compartment_count" for name in CONTENT_TYPES.values()]

    all_cols = [
        "ship_version_id",
        *volume_cols,
        "total_compartment_volume",
        *ratio_cols,
    ]

    if comp_df.empty:
        return pd.DataFrame(columns=all_cols)

    comp_df = comp_df.copy()
    comp_df["content_name"] = comp_df["content_id"].map(CONTENT_TYPES)
    comp_df = comp_df.dropna(subset=["content_name"])

    output = pd.DataFrame(
        {
            "ship_version_id": sorted(comp_df["ship_version_id"].unique()),
        }
    )

    for content_id, content_name in CONTENT_TYPES.items():
        content_df = comp_df[comp_df["content_id"] == content_id]

        volume = (
            content_df
            .groupby("ship_version_id")["compartment_volume"]
            .sum()
            .reset_index(name=f"{content_name}_volume_total")
        )
        output = output.merge(volume, on="ship_version_id", how="left")

    output[volume_cols] = output[volume_cols].fillna(0.0)
    output["total_compartment_volume"] = output[volume_cols].sum(axis=1)

    for content_name in CONTENT_TYPES.values():
        total_col = f"{content_name}_volume_total"
        ratio_col = f"{content_name}_volume_ratio"
        output[ratio_col] = np.where(
            output["total_compartment_volume"] > 0,
            output[total_col] / output["total_compartment_volume"],
            0.0,
        )

    return output[all_cols]


def volume_features_for_ship(conn: object, ship_version_id: int) -> pd.DataFrame:
    points = read_points_for_ship(conn, ship_version_id)

    if points.empty:
        return pd.DataFrame(columns=["ship_version_id"])

    points = clean_points(points)

    if points.empty:
        return pd.DataFrame(columns=["ship_version_id"])

    comp_df = calculate_compartment_volumes(points)

    return aggregate_volume_features(comp_df)


def derive_compartment_volume_by_type(
    conn: object,
    ship_version_ids: list[int] | np.ndarray | None = None,
    progress_callback: object | None = None,
    batch_size: int = 25,
) -> pd.DataFrame:
    """
    Calculate volume features for each requested ship version.
    """
    if ship_version_ids is None:
        ship_ids_df = pd.read_sql_query(
            "SELECT DISTINCT ship_version_id FROM compartment ORDER BY ship_version_id",
            conn,
        )
        ship_version_ids = ship_ids_df["ship_version_id"].dropna().astype(int).tolist()
    else:
        ship_version_ids = [int(ship_id) for ship_id in ship_version_ids]

    outputs = []
    total = len(ship_version_ids)

    for start in range(0, total, batch_size):
        batch = ship_version_ids[start: start + batch_size]
        points = read_points_for_ship_versions(conn, batch)

        if not points.empty:
            points = clean_points(points)
            comp_df = calculate_compartment_volumes(points)
            features = aggregate_volume_features(comp_df)
            outputs.append(features)

        if progress_callback is not None:
            done = min(start + batch_size, total)
            progress_callback(done, total, batch[-1])

    if not outputs:
        return pd.DataFrame(columns=["ship_version_id"])

    return pd.concat(outputs, ignore_index=True)
