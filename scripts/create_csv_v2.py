# Import standard library packages.
import sqlite3

# Import third party packages.
import pandas as pd

# Connect to SQLite database
conn = sqlite3.connect("C:/Users/student01/Desktop/rug-project/pias/localhost.db")

query = """
WITH comp_data AS (
    SELECT
        comp.ship_version_id,

        COUNT(DISTINCT comp.id) AS total_compartments,
        COUNT(DISTINCT sub.id) AS n_subcompartments,

        CAST(COUNT(DISTINCT sub.id) AS REAL) /
            NULLIF(COUNT(DISTINCT comp.id), 0)
            AS subcompartments_per_compartment,

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

        SUM(CASE
            WHEN sub.is_pipe = 1 THEN 1
            ELSE 0
        END) AS n_pipe_subcompartments,

        CAST(SUM(CASE
            WHEN sub.is_pipe = 1 THEN 1
            ELSE 0
        END) AS REAL) /
            NULLIF(COUNT(DISTINCT sub.id), 0)
            AS pipe_subcompartment_ratio,

        -- Content type counts
        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 1 THEN comp.id
        END) AS n_cargo,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 2 THEN comp.id
        END) AS n_fuel_oil,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 3 THEN comp.id
        END) AS n_gas_oil,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 4 THEN comp.id
        END) AS n_potable_water,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 6 THEN comp.id
        END) AS n_ballast,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 8 THEN comp.id
        END) AS n_void,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 12 THEN comp.id
        END) AS n_cargohold_hatch

    FROM compartment comp

    JOIN subcompartment sub
        ON sub.compartment_id = comp.id

    GROUP BY comp.ship_version_id
),

opening_data AS (
    SELECT
        op.ship_version_id,

        COUNT(DISTINCT op.id) AS total_openings,

        AVG(op.length) AS mean_opening_length,
        AVG(op.breadth) AS mean_opening_breadth,
        AVG(op.height) AS mean_opening_height,

        MIN(op.height) AS min_opening_height,
        MAX(op.height) AS max_opening_height,

        AVG(op.length * op.breadth) AS mean_opening_area,
        MAX(op.length * op.breadth) AS max_opening_area,

        COUNT(DISTINCT op.opening_type) AS n_opening_types,

        COUNT(DISTINCT CASE
            WHEN op.connected_compartment IS NOT NULL
                 AND TRIM(op.connected_compartment) <> ''
            THEN op.id
        END) AS n_connected_openings,

        -- Opening position features, if L/B/H columns are populated
        AVG(op.L) AS mean_opening_L,
        AVG(op.B) AS mean_opening_B,
        AVG(op.H) AS mean_opening_H,

        MIN(op.H) AS min_opening_H,
        MAX(op.H) AS max_opening_H,

        CASE
            WHEN (AVG(op.L * op.L) - AVG(op.L) * AVG(op.L)) > 0
            THEN SQRT(AVG(op.L * op.L) - AVG(op.L) * AVG(op.L))
            ELSE 0
        END AS std_opening_L,

        CASE
            WHEN (AVG(op.B * op.B) - AVG(op.B) * AVG(op.B)) > 0
            THEN SQRT(AVG(op.B * op.B) - AVG(op.B) * AVG(op.B))
            ELSE 0
        END AS std_opening_B,

        CASE
            WHEN (AVG(op.H * op.H) - AVG(op.H) * AVG(op.H)) > 0
            THEN SQRT(AVG(op.H * op.H) - AVG(op.H) * AVG(op.H))
            ELSE 0
        END AS std_opening_H

    FROM opening op

    GROUP BY op.ship_version_id
),

geom AS (
    SELECT
        ss.ship_version_id,

        MAX(fp.L) - MIN(fp.L) AS total_layout_length,
        MAX(fp.B) AS max_layout_breadth,
        MAX(fp.H) AS max_layout_height,

        AVG(fp.B * fp.H) AS avg_cross_section,
        SUM(fp.B * fp.H) AS sum_bh_sections,

        CASE
            WHEN (AVG(fp.B * fp.B) - AVG(fp.B) * AVG(fp.B)) > 0
            THEN SQRT(AVG(fp.B * fp.B) - AVG(fp.B) * AVG(fp.B))
            ELSE 0
        END AS std_breadth,

        CASE
            WHEN (AVG(fp.H * fp.H) - AVG(fp.H) * AVG(fp.H)) > 0
            THEN SQRT(AVG(fp.H * fp.H) - AVG(fp.H) * AVG(fp.H))
            ELSE 0
        END AS std_height,

        COUNT(*) AS n_frustum_points,
        COUNT(DISTINCT ss.id) AS n_shapes,
        COUNT(DISTINCT ss.side) AS n_shape_sides

    FROM subcompartment_shape ss

    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id

    GROUP BY ss.ship_version_id
),

main_dims AS (
    SELECT
        md.ship_version_id,

        MAX(md.lpp) AS lpp,
        MAX(md.loa) AS loa,
        MAX(md.breadth) AS breadth,
        MAX(md.depth) AS depth

    FROM main_dimensions md

    GROUP BY md.ship_version_id
)

SELECT
    t.ship_version_id,
    sv.ship_id,

    -- Loading / stability features
    t.draft,
    t.trim,
    t.mg,
    t.displacement,
    t.vcg,
    t.required_index,

    CASE
        WHEN LOWER(t.condition_name) = 'light' THEN 0
        WHEN LOWER(t.condition_name) = 'partial' THEN 1
        WHEN LOWER(t.condition_name) = 'deepest' THEN 2
        ELSE NULL
    END AS condition_code,

    -- Main dimensions
    main_dims.lpp,
    main_dims.loa,
    main_dims.breadth,
    main_dims.depth,

    -- Dimension ratios
    main_dims.lpp / NULLIF(main_dims.breadth, 0)
        AS lpp_over_breadth,

    main_dims.loa / NULLIF(main_dims.breadth, 0)
        AS loa_over_breadth,

    main_dims.breadth / NULLIF(main_dims.depth, 0)
        AS breadth_over_depth,

    t.draft / NULLIF(main_dims.depth, 0)
        AS draft_over_depth,

    t.displacement /
        NULLIF(main_dims.lpp * main_dims.breadth * main_dims.depth, 0)
        AS displacement_over_lbd,

    -- Compartment / subcompartment features
    comp_data.total_compartments,
    comp_data.n_subcompartments,
    comp_data.subcompartments_per_compartment,

    comp_data.avg_permeability,
    comp_data.min_permeability,
    comp_data.max_permeability,
    comp_data.std_permeability,

    comp_data.n_pipe_subcompartments,
    comp_data.pipe_subcompartment_ratio,

    -- Opening count features
    COALESCE(opening_data.total_openings, 0)
        AS total_openings,

    CAST(COALESCE(opening_data.total_openings, 0) AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS openings_per_compartment,

    CAST(COALESCE(opening_data.total_openings, 0) AS REAL) /
        NULLIF(geom.total_layout_length, 0)
        AS openings_per_length,

    -- Opening geometry features
    opening_data.mean_opening_length,
    opening_data.mean_opening_breadth,
    opening_data.mean_opening_height,
    opening_data.min_opening_height,
    opening_data.max_opening_height,

    opening_data.mean_opening_area,
    opening_data.max_opening_area,

    opening_data.n_opening_types,
    opening_data.n_connected_openings,

    -- Opening position features
    opening_data.mean_opening_L,
    opening_data.mean_opening_B,
    opening_data.mean_opening_H,
    opening_data.min_opening_H,
    opening_data.max_opening_H,
    opening_data.std_opening_L,
    opening_data.std_opening_B,
    opening_data.std_opening_H,

    -- Content type counts
    comp_data.n_cargo,
    comp_data.n_fuel_oil,
    comp_data.n_gas_oil,
    comp_data.n_potable_water,
    comp_data.n_ballast,
    comp_data.n_void,
    comp_data.n_cargohold_hatch,

    -- Content type ratios
    CAST(comp_data.n_cargo AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS cargo_ratio,

    CAST(comp_data.n_fuel_oil AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS fuel_oil_ratio,

    CAST(comp_data.n_gas_oil AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS gas_oil_ratio,

    CAST(comp_data.n_potable_water AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS potable_water_ratio,

    CAST(comp_data.n_ballast AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS ballast_ratio,

    CAST(comp_data.n_void AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS void_ratio,

    CAST(comp_data.n_cargohold_hatch AS REAL) /
        NULLIF(comp_data.total_compartments, 0)
        AS cargohold_hatch_ratio,

    -- Layout / geometry features
    geom.total_layout_length,
    geom.max_layout_breadth,
    geom.max_layout_height,
    geom.avg_cross_section,
    geom.sum_bh_sections,
    geom.std_breadth,
    geom.std_height,
    geom.n_frustum_points,
    geom.n_shapes,
    geom.n_shape_sides,

    -- Geometry ratios
    geom.total_layout_length / NULLIF(geom.max_layout_breadth, 0)
        AS layout_length_over_breadth,

    geom.max_layout_breadth / NULLIF(t.draft, 0)
        AS layout_breadth_over_draft,

    geom.max_layout_height / NULLIF(t.draft, 0)
        AS layout_height_over_draft,

    comp_data.total_compartments / NULLIF(geom.total_layout_length, 0)
        AS compartments_per_length,

    -- Targets
    t.attained_index AS target_attained_index,

    (t.attained_index - t.required_index)
        AS target_margin

FROM trim_gm t

JOIN ship_version sv
    ON sv.id = t.ship_version_id

LEFT JOIN main_dims
    ON main_dims.ship_version_id = t.ship_version_id

LEFT JOIN comp_data
    ON comp_data.ship_version_id = t.ship_version_id

LEFT JOIN opening_data
    ON opening_data.ship_version_id = t.ship_version_id

LEFT JOIN geom
    ON geom.ship_version_id = t.ship_version_id

WHERE comp_data.avg_permeability IS NOT NULL
    AND comp_data.total_compartments IS NOT NULL
    AND t.attained_index IS NOT NULL
    AND LOWER(t.condition_name) = 'partial'

ORDER BY
    t.ship_version_id,
    condition_code;
"""


def test_entire_table_queries(conn):
    print(pd.read_sql("SELECT COUNT(*) FROM trim_gm", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM main_dimensions", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM compartment", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM subcompartment", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM subcompartment_shape", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM frustum_point", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM opening", conn))


def test_ctes_query(conn):
    print(
        pd.read_sql(
            """
            WITH comp_data AS (
                SELECT
                    comp.ship_version_id,
                    COUNT(DISTINCT comp.id) AS total_compartments,
                    COUNT(DISTINCT sub.id) AS n_subcompartments,
                    AVG(sub.permeability_for_damage_stability) AS avg_permeability
                FROM compartment comp
                JOIN subcompartment sub
                    ON sub.compartment_id = comp.id
                GROUP BY comp.ship_version_id
            )
            SELECT * FROM comp_data
            """,
            conn,
        )
    )


def test_geom_query(conn):
    print(
        pd.read_sql(
            """
            WITH geom AS (
                SELECT
                    ss.ship_version_id,
                    COUNT(*) AS n_frustum_points,
                    MAX(fp.L) - MIN(fp.L) AS total_layout_length
                FROM subcompartment_shape ss
                JOIN frustum_point fp
                    ON fp.subcompartment_shape_id = ss.id
                GROUP BY ss.ship_version_id
            )
            SELECT * FROM geom
            """,
            conn,
        )
    )


def test_opening_query(conn):
    print(
        pd.read_sql(
            """
            WITH opening_data AS (
                SELECT
                    op.ship_version_id,
                    COUNT(DISTINCT op.id) AS total_openings,
                    AVG(op.length * op.breadth) AS mean_opening_area,
                    COUNT(DISTINCT op.opening_type) AS n_opening_types
                FROM opening op
                GROUP BY op.ship_version_id
            )
            SELECT * FROM opening_data
            """,
            conn,
        )
    )


# Perform test queries.
test_entire_table_queries(conn)
test_ctes_query(conn)
test_geom_query(conn)
test_opening_query(conn)

# Execute query and load into DataFrame
df = pd.read_sql_query(query, conn)

# Show results
print(df.head())
print(df.shape)
print(df.columns)

# Optional: save results
df.to_csv("data/all_ships_partial_v6.csv", index=False)

# Close connection
conn.close()