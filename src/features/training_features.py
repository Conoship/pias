import sqlite3

import pandas as pd

from src.features.volume_features import derive_compartment_volume_by_type


TRAINING_FEATURE_QUERY = """
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


def build_training_features(
    conn: sqlite3.Connection,
    verbose: bool = False,
) -> pd.DataFrame:
    if verbose:
        print("Building base training features...", flush=True)

    features_df = pd.read_sql_query(TRAINING_FEATURE_QUERY, conn)

    if verbose:
        print(f"Base feature rows: {len(features_df)}", flush=True)
        print("Building volume features...", flush=True)

    ship_version_ids = features_df["ship_version_id"].dropna().astype(int).unique()

    def print_progress(done: int, total: int, ship_id: int) -> None:
        if verbose:
            print(
                f"Processed volume features up to ship_version_id={ship_id} "
                f"({done}/{total})",
                flush=True,
            )

    volume_features = derive_compartment_volume_by_type(
        conn,
        ship_version_ids=ship_version_ids,
        progress_callback=print_progress if verbose else None,
    )

    if verbose:
        print(f"Volume feature rows: {len(volume_features)}", flush=True)

    return features_df.merge(
        volume_features,
        on="ship_version_id",
        how="left",
    )
