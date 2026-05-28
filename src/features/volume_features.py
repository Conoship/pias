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


def derive_compartment_volume_by_type(conn: object) -> pd.DataFrame:
    """
    Derive compartment volume per type for each ship_version_id.
    """

    #  Load geometry points from database
    points = pd.read_sql_query(
        """
        SELECT
            comp.ship_version_id,
            comp.id AS compartment_id,
            comp.design_content_id_number AS content_id,

            sub.id AS subcompartment_id,
            COALESCE(sub.sign, 1) AS sign,
            ss.side,

            md.breadth / 2.0 AS half_breadth,

            fp.L,
            fp.B,
            COALESCE(fp.H, 0) AS H

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

        WHERE fp.L IS NOT NULL
        """,
        conn,
    )

    if points.empty:
        return pd.DataFrame(columns=["ship_version_id"])

    points = fill_missing_breadth(points)

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
