import sqlite3

import pandas as pd

from src.features.opening_features import derive_opening_risk_features
from src.features.volume_features import derive_compartment_volume_by_type

TRAINING_FEATURE_QUERY = """
WITH
comp_counts AS (
    SELECT
        comp.ship_version_id,

        COUNT(DISTINCT comp.id) AS total_compartments,

        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 1 THEN comp.id END)
            AS n_cargo,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 2 THEN comp.id END)
            AS n_fuel_oil,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 3 THEN comp.id END)
            AS n_gas_oil,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 4 THEN comp.id END)
            AS n_potable_water,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 6 THEN comp.id END)
            AS n_ballast,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 8 THEN comp.id END)
            AS n_void,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number = 12 THEN comp.id END)
            AS n_cargohold_hatch,
        COUNT(DISTINCT CASE WHEN comp.design_content_id_number IS NULL THEN comp.id END)
            AS n_unknown_content

    FROM compartment comp
    GROUP BY comp.ship_version_id
),

sub_data AS (
    SELECT
        comp.ship_version_id,

        COUNT(DISTINCT sub.id) AS n_subcompartments,

        AVG(sub.permeability_for_damage_stability) AS avg_permeability,
        MIN(sub.permeability_for_damage_stability) AS min_permeability,
        MAX(sub.permeability_for_damage_stability) AS max_permeability,

        CASE
            WHEN (
                AVG(sub.permeability_for_damage_stability * sub.permeability_for_damage_stability)
                - AVG(sub.permeability_for_damage_stability)
                  * AVG(sub.permeability_for_damage_stability)
            ) > 0
            THEN SQRT(
                AVG(sub.permeability_for_damage_stability * sub.permeability_for_damage_stability)
                - AVG(sub.permeability_for_damage_stability)
                  * AVG(sub.permeability_for_damage_stability)
            )
            ELSE 0
        END AS std_permeability,

        SUM(CASE WHEN sub.is_pipe = 1 THEN 1 ELSE 0 END) AS n_pipe_subcompartments

    FROM compartment comp
    JOIN subcompartment sub
        ON sub.compartment_id = comp.id
    GROUP BY comp.ship_version_id
),

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

cargo_bounds AS (
    SELECT
        comp.ship_version_id,
        MIN(fp.L) AS cargo_min_L,
        MAX(fp.L) AS cargo_max_L

    FROM compartment comp

    JOIN subcompartment sub
        ON sub.compartment_id = comp.id

    JOIN subcompartment_shape ss
        ON ss.shape_guid = sub.shape_guid
       AND ss.ship_version_id = comp.ship_version_id

    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id

    WHERE fp.L IS NOT NULL
      AND comp.design_content_id_number IN (1, 12)

    GROUP BY comp.ship_version_id
),

main_dims_by_ship AS (
    SELECT
        sv.ship_id,
        AVG(md.lpp) AS lpp,
        AVG(md.loa) AS loa,
        AVG(md.breadth) AS breadth,
        AVG(md.depth) AS depth
    FROM main_dimensions md
    JOIN ship_version sv
        ON sv.id = md.ship_version_id
    GROUP BY sv.ship_id
),

comp_perm AS (
    SELECT
        comp.ship_version_id,
        comp.id AS compartment_id,

        AVG(sub.permeability_for_damage_stability) AS comp_avg_permeability

    FROM compartment comp
    LEFT JOIN subcompartment sub
        ON sub.compartment_id = comp.id

    GROUP BY
        comp.ship_version_id,
        comp.id
),

comp_l_position AS (
    SELECT
        comp.ship_version_id,
        comp.id AS compartment_id,
        comp.design_content_id_number,

        AVG(fp.L) AS comp_center_L

    FROM compartment comp

    LEFT JOIN subcompartment sub
        ON sub.compartment_id = comp.id

    LEFT JOIN subcompartment_shape ss
        ON ss.shape_guid = sub.shape_guid
       AND ss.ship_version_id = comp.ship_version_id

    LEFT JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id
       AND fp.L IS NOT NULL

    GROUP BY
        comp.ship_version_id,
        comp.id,
        comp.design_content_id_number
),

comp_position AS (
    SELECT
        clp.ship_version_id,
        clp.compartment_id,
        clp.design_content_id_number,

        clp.comp_center_L,
        cb.cargo_min_L,
        cb.cargo_max_L,

        (
            clp.comp_center_L - sb.ship_min_L
        ) / NULLIF(sb.total_layout_length, 0)
            AS comp_norm_L,

        cp.comp_avg_permeability

    FROM comp_l_position clp

    LEFT JOIN ship_bounds sb
        ON sb.ship_version_id = clp.ship_version_id

    LEFT JOIN cargo_bounds cb
        ON cb.ship_version_id = clp.ship_version_id

    LEFT JOIN comp_perm cp
        ON cp.ship_version_id = clp.ship_version_id
       AND cp.compartment_id = clp.compartment_id
),

zone_data AS (
    SELECT
        ship_version_id,

        SUM(CASE
            WHEN comp_center_L < cargo_min_L
            THEN 1 ELSE 0
        END)
            AS n_comp_aft,

        SUM(CASE
            WHEN comp_center_L >= cargo_min_L
             AND comp_center_L <= cargo_max_L
            THEN 1 ELSE 0
        END) AS n_comp_mid,

        SUM(CASE
            WHEN comp_center_L > cargo_max_L
            THEN 1 ELSE 0
        END)
            AS n_comp_fwd,

        SUM(CASE
            WHEN comp_center_L IS NULL
              OR cargo_min_L IS NULL
              OR cargo_max_L IS NULL
            THEN 1 ELSE 0
        END)
            AS n_comp_unknown_zone,

        AVG(CASE
            WHEN comp_center_L < cargo_min_L
            THEN comp_avg_permeability
        END) AS avg_perm_aft,

        AVG(CASE
            WHEN comp_center_L >= cargo_min_L
             AND comp_center_L <= cargo_max_L
            THEN comp_avg_permeability
        END) AS avg_perm_mid,

        AVG(CASE
            WHEN comp_center_L > cargo_max_L
            THEN comp_avg_permeability
        END) AS avg_perm_fwd,

        SUM(CASE
            WHEN comp_center_L < cargo_min_L
             AND design_content_id_number = 8
            THEN 1 ELSE 0
        END) AS n_void_aft,

        SUM(CASE
            WHEN comp_center_L >= cargo_min_L
             AND comp_center_L <= cargo_max_L
             AND design_content_id_number = 8
            THEN 1 ELSE 0
        END) AS n_void_mid,

        SUM(CASE
            WHEN comp_center_L > cargo_max_L
             AND design_content_id_number = 8
            THEN 1 ELSE 0
        END) AS n_void_fwd,

        SUM(CASE
            WHEN comp_center_L < cargo_min_L
             AND design_content_id_number = 6
            THEN 1 ELSE 0
        END) AS n_ballast_aft,

        SUM(CASE
            WHEN comp_center_L >= cargo_min_L
             AND comp_center_L <= cargo_max_L
             AND design_content_id_number = 6
            THEN 1 ELSE 0
        END) AS n_ballast_mid,

        SUM(CASE
            WHEN comp_center_L > cargo_max_L
             AND design_content_id_number = 6
            THEN 1 ELSE 0
        END) AS n_ballast_fwd

    FROM comp_position
    GROUP BY ship_version_id
),

opening_norm AS (
    SELECT
        op.ship_version_id,
        op.id,
        op.length,
        op.breadth,
        op.height,
        op.opening_type,
        op.connected_compartment,
        op.L,
        op.H,
        cb.cargo_min_L,
        cb.cargo_max_L,

        (
            op.L - sb.ship_min_L
        ) / NULLIF(sb.total_layout_length, 0)
            AS opening_l_norm

    FROM opening op

    LEFT JOIN ship_bounds sb
        ON sb.ship_version_id = op.ship_version_id

    LEFT JOIN cargo_bounds cb
        ON cb.ship_version_id = op.ship_version_id
),

opening_data AS (
    SELECT
        ship_version_id,

        COUNT(DISTINCT id) AS total_openings,

        AVG(length) AS mean_opening_length,
        AVG(breadth) AS mean_opening_breadth,
        AVG(height) AS mean_opening_height,
        AVG(length * breadth) AS mean_opening_area,
        MAX(length * breadth) AS max_opening_area,

        COUNT(DISTINCT CASE
            WHEN opening_type IS NOT NULL
             AND TRIM(opening_type) <> ''
            THEN opening_type
        END) AS n_opening_types,

        COUNT(DISTINCT CASE
            WHEN connected_compartment IS NOT NULL
             AND TRIM(connected_compartment) <> ''
             AND TRIM(connected_compartment) <> '-'
            THEN id
        END) AS n_connected_openings,

        SUM(CASE
            WHEN L < cargo_min_L
            THEN 1 ELSE 0
        END)
            AS n_openings_aft,

        SUM(CASE
            WHEN L >= cargo_min_L
             AND L <= cargo_max_L
            THEN 1 ELSE 0
        END) AS n_openings_mid,

        SUM(CASE
            WHEN L > cargo_max_L
            THEN 1 ELSE 0
        END)
            AS n_openings_fwd,

        SUM(CASE
            WHEN L IS NULL
              OR cargo_min_L IS NULL
              OR cargo_max_L IS NULL
            THEN 1 ELSE 0
        END)
            AS n_openings_unknown_zone

    FROM opening_norm
    GROUP BY ship_version_id
)

SELECT
    t.ship_version_id,
    sv.ship_id,

    t.draft,
    t.trim,
    t.displacement,

    CASE
        WHEN LOWER(t.condition_name) = 'light' THEN 0
        WHEN LOWER(t.condition_name) = 'partial' THEN 1
        WHEN LOWER(t.condition_name) = 'deepest' THEN 2
        ELSE NULL
    END AS condition_code,

    t.mg,
    t.vcg,

    CASE WHEN md.lpp IS NULL THEN 1 ELSE 0 END AS main_dimensions_missing,

    COALESCE(md.lpp, ship_bounds.total_layout_length) AS lpp,
    COALESCE(md.loa, ship_bounds.total_layout_length) AS loa,
    md.breadth,
    md.depth,

    COALESCE(md.lpp, ship_bounds.total_layout_length)
        / NULLIF(md.breadth, 0)
        AS slenderness_ratio,

    md.breadth / NULLIF(md.depth, 0)
        AS breadth_depth_ratio,

    md.breadth / NULLIF(md.depth, 0)
        AS breath_depth_ratio,

    md.loa * md.breadth * md.depth
        AS box_volume,

    comp_counts.total_compartments,
    sub_data.n_subcompartments,

    CAST(sub_data.n_subcompartments AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS subcompartments_per_compartment,

    sub_data.avg_permeability,
    sub_data.min_permeability,
    sub_data.max_permeability,
    sub_data.std_permeability,
    sub_data.n_pipe_subcompartments,

    CAST(sub_data.n_pipe_subcompartments AS REAL)
        / NULLIF(sub_data.n_subcompartments, 0)
        AS pipe_subcompartment_ratio,

    comp_counts.n_cargo,
    comp_counts.n_fuel_oil,
    comp_counts.n_gas_oil,
    comp_counts.n_potable_water,
    comp_counts.n_ballast,
    comp_counts.n_void,
    comp_counts.n_cargohold_hatch,
    comp_counts.n_unknown_content,

    CAST(comp_counts.n_cargo AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS cargo_ratio,

    CAST(comp_counts.n_fuel_oil AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS fuel_oil_ratio,

    CAST(comp_counts.n_gas_oil AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS gas_oil_ratio,

    CAST(comp_counts.n_potable_water AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS potable_water_ratio,

    CAST(comp_counts.n_ballast AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS ballast_ratio,

    CAST(comp_counts.n_void AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS void_ratio,

    CAST(comp_counts.n_cargohold_hatch AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS cargohold_hatch_ratio,

    ship_bounds.total_layout_length,

    ship_bounds.total_layout_length
        / NULLIF(COALESCE(md.lpp, ship_bounds.total_layout_length), 0)
        AS layout_length_lpp_ratio,

    CAST(comp_counts.total_compartments AS REAL)
        / NULLIF(COALESCE(md.lpp, ship_bounds.total_layout_length), 0)
        AS compartments_per_meter,

    COALESCE(opening_data.total_openings, 0) AS total_openings,

    CAST(COALESCE(opening_data.total_openings, 0) AS REAL)
        / NULLIF(comp_counts.total_compartments, 0)
        AS openings_per_compartment,

    CAST(COALESCE(opening_data.total_openings, 0) AS REAL)
        / NULLIF(COALESCE(md.lpp, ship_bounds.total_layout_length), 0)
        AS openings_per_meter,

    opening_data.mean_opening_length,
    opening_data.mean_opening_breadth,
    opening_data.mean_opening_height,
    opening_data.mean_opening_area,
    opening_data.max_opening_area,

    COALESCE(opening_data.n_opening_types, 0) AS n_opening_types,
    COALESCE(opening_data.n_connected_openings, 0) AS n_connected_openings,

    COALESCE(zone_data.n_comp_aft, 0) AS n_comp_aft,
    COALESCE(zone_data.n_comp_mid, 0) AS n_comp_mid,
    COALESCE(zone_data.n_comp_fwd, 0) AS n_comp_fwd,
    COALESCE(zone_data.n_comp_unknown_zone, 0) AS n_comp_unknown_zone,

    zone_data.avg_perm_aft,
    zone_data.avg_perm_mid,
    zone_data.avg_perm_fwd,

    COALESCE(zone_data.n_void_aft, 0) AS n_void_aft,
    COALESCE(zone_data.n_void_mid, 0) AS n_void_mid,
    COALESCE(zone_data.n_void_fwd, 0) AS n_void_fwd,

    COALESCE(zone_data.n_ballast_aft, 0) AS n_ballast_aft,
    COALESCE(zone_data.n_ballast_mid, 0) AS n_ballast_mid,
    COALESCE(zone_data.n_ballast_fwd, 0) AS n_ballast_fwd,

    COALESCE(opening_data.n_openings_aft, 0) AS n_openings_aft,
    COALESCE(opening_data.n_openings_mid, 0) AS n_openings_mid,
    COALESCE(opening_data.n_openings_fwd, 0) AS n_openings_fwd,
    COALESCE(opening_data.n_openings_unknown_zone, 0) AS n_openings_unknown_zone,

    COALESCE(md.breadth, 0)
        / NULLIF(COALESCE(md.depth, 0), 0)
        AS breadth_over_depth,

    t.draft / NULLIF(COALESCE(md.depth, 0), 0)
        AS draft_over_depth,

    t.displacement / NULLIF(COALESCE(md.lpp, ship_bounds.total_layout_length), 0)
        AS displacement_per_length,

    t.required_index,
    t.attained_index AS target_attained_index,
    t.attained_index - t.required_index AS target_margin

FROM trim_gm t

JOIN ship_version sv
    ON sv.id = t.ship_version_id

LEFT JOIN main_dims_by_ship md
    ON md.ship_id = sv.ship_id

LEFT JOIN ship_bounds
    ON ship_bounds.ship_version_id = t.ship_version_id

LEFT JOIN comp_counts
    ON comp_counts.ship_version_id = t.ship_version_id

LEFT JOIN sub_data
    ON sub_data.ship_version_id = t.ship_version_id

LEFT JOIN zone_data
    ON zone_data.ship_version_id = t.ship_version_id

LEFT JOIN opening_data
    ON opening_data.ship_version_id = t.ship_version_id

WHERE t.attained_index IS NOT NULL
    AND comp_counts.total_compartments IS NOT NULL
    AND sub_data.avg_permeability IS NOT NULL

ORDER BY
    t.ship_version_id,
    condition_code;
"""


def build_training_features(
    conn: sqlite3.Connection,
    verbose: bool = False,
) -> pd.DataFrame:

    features_df = pd.read_sql_query(TRAINING_FEATURE_QUERY, conn)
    ship_version_ids = features_df["ship_version_id"].dropna().astype(int).unique()

    def print_progress(
        done: int,
        total: int,
        ship_id: int,
        rows_loaded: int,
        load_seconds: float,
        batch_seconds: float,
    ) -> None:
        if verbose:
            print(
                f"Processed volume features up to ship_version_id={ship_id} "
                f"({done}/{total}); loaded {rows_loaded} rows in "
                f"{load_seconds:.1f}s, batch {batch_seconds:.1f}s",
                flush=True,
            )

    volume_features = derive_compartment_volume_by_type(
        conn,
        ship_version_ids=ship_version_ids,
        progress_callback=print_progress if verbose else None,
    )
    opening_features = derive_opening_risk_features(
        conn,
        ship_version_ids=ship_version_ids,
    )

    if verbose:
        print(f"Volume feature rows: {len(volume_features)}", flush=True)
        print(f"Opening feature rows: {len(opening_features)}", flush=True)

    for extra_features in [volume_features, opening_features]:
        if "ship_version_id" in extra_features.columns:
            extra_features["ship_version_id"] = pd.to_numeric(
                extra_features["ship_version_id"],
                errors="coerce",
            ).astype("Int64")

    features_df["ship_version_id"] = features_df["ship_version_id"].astype("Int64")

    return features_df.merge(
        volume_features,
        on="ship_version_id",
        how="left",
    ).merge(
        opening_features,
        on="ship_version_id",
        how="left",
    )
