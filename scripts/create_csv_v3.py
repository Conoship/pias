# Import standard library packages.
import sqlite3

# Import third party packages.
import numpy as np
import pandas as pd

# Connect to SQLite database
conn = sqlite3.connect("C:/Users/student01/Desktop/rug-project/pias/localhost.db")

query = """
WITH
ship_bounds AS (
    SELECT
        ss.ship_version_id,
        MIN(fp.L) AS ship_min_L,
        MAX(fp.L) AS ship_max_L,
        MAX(fp.L) - MIN(fp.L) AS total_layout_length
    FROM subcompartment_shape ss
    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id
    WHERE fp.L IS NOT NULL
    GROUP BY ss.ship_version_id
),

main_dims_by_ship AS (
    SELECT
        sv.ship_id,
        AVG(md.lpp) AS lpp,
        AVG(md.depth) AS depth
    FROM main_dimensions md
    JOIN ship_version sv
        ON sv.id = md.ship_version_id
    GROUP BY sv.ship_id
),

comp_exists AS (
    SELECT
        ship_version_id,
        COUNT(DISTINCT id) AS total_compartments
    FROM compartment
    GROUP BY ship_version_id
)

SELECT
    t.ship_version_id,
    sv.ship_id,

    CASE
        WHEN LOWER(t.condition_name) = 'light' THEN 0
        WHEN LOWER(t.condition_name) = 'partial' THEN 1
        WHEN LOWER(t.condition_name) = 'deepest' THEN 2
        ELSE NULL
    END AS condition_code,

    t.mg,
    t.vcg,
    t.trim,

    t.draft / NULLIF(md.depth, 0)
        AS draft_over_depth,

    t.displacement / NULLIF(COALESCE(md.lpp, ship_bounds.total_layout_length), 0)
        AS displacement_per_length,

    t.attained_index AS target_attained_index

FROM trim_gm t

JOIN ship_version sv
    ON sv.id = t.ship_version_id

LEFT JOIN main_dims_by_ship md
    ON md.ship_id = sv.ship_id

LEFT JOIN ship_bounds
    ON ship_bounds.ship_version_id = t.ship_version_id

JOIN comp_exists
    ON comp_exists.ship_version_id = t.ship_version_id

WHERE t.attained_index IS NOT NULL

ORDER BY
    t.ship_version_id,
    condition_code;
"""

CONTENT_MAP = {
    1: "cargo",
    2: "fuel_oil",
    3: "gas_oil",
    4: "potable_water",
    6: "ballast",
    8: "void",
    12: "cargohold_hatch",
}


def polygon_area(section):
    """Calculate the area of one B-H cross-section."""
    pts = section[["B", "H"]].dropna().drop_duplicates().to_numpy()

    if len(pts) < 3:
        return 0.0

    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    pts = pts[np.argsort(angles)]

    b = pts[:, 0]
    h = pts[:, 1]

    return 0.5 * abs(np.dot(b, np.roll(h, -1)) - np.dot(h, np.roll(b, -1)))


def subcompartment_volume(points):
    """Estimate volume by integrating section area along L."""
    if points.empty:
        return 0.0

    points = points.copy()
    points["L_round"] = points["L"].round(6)

    areas = (
        points.groupby("L_round")
        .apply(polygon_area)
        .reset_index(name="area")
        .sort_values("L_round")
    )

    if len(areas) < 2:
        return 0.0

    return abs(np.trapz(areas["area"], areas["L_round"]))


def derive_compartment_volume_by_type(conn):
    points = pd.read_sql_query(
        """
        SELECT
            comp.ship_version_id,
            comp.id AS compartment_id,
            comp.design_content_id_number,
            sub.id AS subcompartment_id,
            COALESCE(sub.sign, 1) AS sign,
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
        WHERE fp.L IS NOT NULL
          AND fp.B IS NOT NULL
          AND fp.H IS NOT NULL
        """,
        conn,
    )

    rows = []

    for keys, grp in points.groupby(
        [
            "ship_version_id",
            "compartment_id",
            "design_content_id_number",
            "subcompartment_id",
            "sign",
        ],
        dropna=False,
    ):
        ship_version_id, compartment_id, content_id, sub_id, sign = keys

        rows.append(
            {
                "ship_version_id": ship_version_id,
                "compartment_id": compartment_id,
                "content_id": content_id,
                "subcompartment_volume": subcompartment_volume(grp)
                * float(sign),
            }
        )

    sub_volumes = pd.DataFrame(rows)

    comp_volumes = (
        sub_volumes.groupby(
            ["ship_version_id", "compartment_id", "content_id"],
            as_index=False,
        )
        .agg(compartment_volume=("subcompartment_volume", "sum"))
    )

    comp_volumes["compartment_volume"] = comp_volumes[
        "compartment_volume"
    ].clip(lower=0)

    comp_volumes["content_type"] = comp_volumes["content_id"].map(CONTENT_MAP)
    comp_volumes["content_type"] = comp_volumes["content_type"].fillna("unknown")

    volume_by_type = (
        comp_volumes.pivot_table(
            index="ship_version_id",
            columns="content_type",
            values="compartment_volume",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    volume_by_type.columns = [
        "ship_version_id"
        if col == "ship_version_id"
        else f"{col}_volume_total"
        for col in volume_by_type.columns
    ]

    volume_cols = [
        col for col in volume_by_type.columns if col.endswith("_volume_total")
    ]

    volume_by_type["total_compartment_volume"] = volume_by_type[
        volume_cols
    ].sum(axis=1)

    for col in volume_cols:
        base = col.replace("_volume_total", "")
        volume_by_type[f"{base}_volume_ratio"] = (
            volume_by_type[col] / volume_by_type["total_compartment_volume"]
        ).replace([np.inf, -np.inf], 0).fillna(0)

    return volume_by_type


# Execute query and load into DataFrame
df = pd.read_sql_query(query, conn)

volume_features = derive_compartment_volume_by_type(conn)
df = df.merge(volume_features, on="ship_version_id", how="left")

# Show results
print(df.head())

# Optional: save results
df.to_csv("data/all_ships_v8_partial.csv", index=False)

# Close connection
conn.close()
