# Import standard library packages.
import sqlite3

# Import third party packages.
import pandas as pd

# Connect to SQLite database
conn = sqlite3.connect("C:/Users/student01/Desktop/rug-project/pias/localhost.db")

query = """
WITH ship_bounds AS (
    SELECT
        ss.ship_version_id,
        MIN(fp.L) AS min_l,
        MAX(fp.L) AS max_l,
        MAX(fp.B) AS max_layout_breadth,
        MAX(fp.H) AS max_layout_height,
        MAX(fp.L) - MIN(fp.L) AS total_layout_length
    FROM subcompartment_shape ss
    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id
    GROUP BY ss.ship_version_id
),

shape_geom AS (
    SELECT
        ss.ship_version_id,
        ss.shape_guid,

        MIN(fp.L) AS shape_min_l,
        MAX(fp.L) AS shape_max_l,
        (MIN(fp.L) + MAX(fp.L)) / 2.0 AS shape_mid_l,

        MAX(fp.L) - MIN(fp.L) AS shape_length,
        AVG(fp.B) AS avg_shape_breadth,
        AVG(fp.H) AS avg_shape_height,
        AVG(fp.B * fp.H) AS avg_shape_cross_section,

        (
            ((MIN(fp.L) + MAX(fp.L)) / 2.0) - sb.min_l
        ) / NULLIF(sb.max_l - sb.min_l, 0) AS rel_l_pos

    FROM subcompartment_shape ss
    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id
    JOIN ship_bounds sb
        ON sb.ship_version_id = ss.ship_version_id
    GROUP BY
        ss.ship_version_id,
        ss.shape_guid
),

comp_data AS (
    SELECT
        comp.ship_version_id,

        COUNT(DISTINCT comp.id) AS total_compartments,
        COUNT(DISTINCT sub.id) AS total_subcompartments,

        AVG(sub.permeability_for_damage_stability) AS avg_permeability,
        MIN(sub.permeability_for_damage_stability) AS min_permeability,
        MAX(sub.permeability_for_damage_stability) AS max_permeability,

        AVG(sg.shape_length) AS avg_compartment_length,
        MAX(sg.shape_length) AS max_compartment_length,

        SQRT(
            MAX(
                0,
                AVG(sg.shape_length * sg.shape_length)
                - AVG(sg.shape_length) * AVG(sg.shape_length)
            )
        ) AS std_compartment_length,

        AVG(sg.avg_shape_cross_section) AS avg_compartment_cross_section,
        MAX(sg.avg_shape_cross_section) AS max_compartment_cross_section,

        MAX(sg.shape_length)
            / NULLIF(SUM(sg.shape_length), 0) AS largest_length_ratio,

        MAX(sg.avg_shape_cross_section)
            / NULLIF(SUM(sg.avg_shape_cross_section), 0) AS largest_cross_section_ratio,

        -- Longitudinal compartment distribution
        COUNT(DISTINCT CASE
            WHEN sg.rel_l_pos < 0.33 THEN comp.id
        END) AS n_compartments_aft,

        COUNT(DISTINCT CASE
            WHEN sg.rel_l_pos >= 0.33 AND sg.rel_l_pos < 0.66 THEN comp.id
        END) AS n_compartments_mid,

        COUNT(DISTINCT CASE
            WHEN sg.rel_l_pos >= 0.66 THEN comp.id
        END) AS n_compartments_forward,

        -- Permeability by region
        AVG(CASE
            WHEN sg.rel_l_pos < 0.33
            THEN sub.permeability_for_damage_stability
        END) AS avg_perm_aft,

        AVG(CASE
            WHEN sg.rel_l_pos >= 0.33 AND sg.rel_l_pos < 0.66
            THEN sub.permeability_for_damage_stability
        END) AS avg_perm_mid,

        AVG(CASE
            WHEN sg.rel_l_pos >= 0.66
            THEN sub.permeability_for_damage_stability
        END) AS avg_perm_forward,

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
        END) AS n_cargohold_hatch,

        -- Cargo distribution
        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 1 AND sg.rel_l_pos < 0.33
            THEN comp.id
        END) AS n_cargo_aft,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 1
             AND sg.rel_l_pos >= 0.33 AND sg.rel_l_pos < 0.66
            THEN comp.id
        END) AS n_cargo_mid,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 1 AND sg.rel_l_pos >= 0.66
            THEN comp.id
        END) AS n_cargo_forward,

        -- Ballast distribution
        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 6 AND sg.rel_l_pos < 0.33
            THEN comp.id
        END) AS n_ballast_aft,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 6
             AND sg.rel_l_pos >= 0.33 AND sg.rel_l_pos < 0.66
            THEN comp.id
        END) AS n_ballast_mid,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 6 AND sg.rel_l_pos >= 0.66
            THEN comp.id
        END) AS n_ballast_forward,

        -- Void distribution
        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 8 AND sg.rel_l_pos < 0.33
            THEN comp.id
        END) AS n_void_aft,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 8
             AND sg.rel_l_pos >= 0.33 AND sg.rel_l_pos < 0.66
            THEN comp.id
        END) AS n_void_mid,

        COUNT(DISTINCT CASE
            WHEN comp.design_content_id_number = 8 AND sg.rel_l_pos >= 0.66
            THEN comp.id
        END) AS n_void_forward

    FROM compartment comp
    JOIN subcompartment sub
        ON sub.compartment_id = comp.id
    LEFT JOIN shape_geom sg
        ON sg.ship_version_id = comp.ship_version_id
        AND sg.shape_guid = sub.shape_guid

    GROUP BY comp.ship_version_id
),

opening_data AS (
    SELECT
        op.ship_version_id,

        COUNT(DISTINCT op.id) AS total_openings,

        CAST(COUNT(DISTINCT op.id) AS REAL)
            / NULLIF(COUNT(DISTINCT comp.id), 0) AS openings_per_compartment,

        AVG(op.height) AS avg_opening_height,
        MAX(op.height) AS max_opening_height,

        AVG(COALESCE(op.length * op.height, op.breadth * op.height))
            AS avg_opening_area,

        MAX(COALESCE(op.length * op.height, op.breadth * op.height))
            AS max_opening_area,

        -- Opening longitudinal distribution
        COUNT(DISTINCT CASE
            WHEN ((op.L - sb.min_l) / NULLIF(sb.max_l - sb.min_l, 0)) < 0.33
            THEN op.id
        END) AS n_openings_aft,

        COUNT(DISTINCT CASE
            WHEN ((op.L - sb.min_l) / NULLIF(sb.max_l - sb.min_l, 0)) >= 0.33
             AND ((op.L - sb.min_l) / NULLIF(sb.max_l - sb.min_l, 0)) < 0.66
            THEN op.id
        END) AS n_openings_mid,

        COUNT(DISTINCT CASE
            WHEN ((op.L - sb.min_l) / NULLIF(sb.max_l - sb.min_l, 0)) >= 0.66
            THEN op.id
        END) AS n_openings_forward,

        -- Opening vertical distribution
        COUNT(DISTINCT CASE
            WHEN op.H / NULLIF(sb.max_layout_height, 0) < 0.33
            THEN op.id
        END) AS n_openings_low,

        COUNT(DISTINCT CASE
            WHEN op.H / NULLIF(sb.max_layout_height, 0) >= 0.33
             AND op.H / NULLIF(sb.max_layout_height, 0) < 0.66
            THEN op.id
        END) AS n_openings_middle_height,

        COUNT(DISTINCT CASE
            WHEN op.H / NULLIF(sb.max_layout_height, 0) >= 0.66
            THEN op.id
        END) AS n_openings_high

    FROM opening op
    LEFT JOIN compartment comp
        ON comp.id = op.compartment_id
    LEFT JOIN ship_bounds sb
        ON sb.ship_version_id = op.ship_version_id

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

        SQRT(
            MAX(
                0,
                AVG(fp.B * fp.B) - AVG(fp.B) * AVG(fp.B)
            )
        ) AS std_breadth,

        SQRT(
            MAX(
                0,
                AVG(fp.H * fp.H) - AVG(fp.H) * AVG(fp.H)
            )
        ) AS std_height,

        COUNT(*) AS n_frustum_points

    FROM subcompartment_shape ss
    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id

    GROUP BY ss.ship_version_id
)

SELECT
    t.ship_version_id,
    sv.ship_id,

    -- Loading features
    t.draft,
    t.displacement,
    t.vcg,

    CASE
        WHEN LOWER(t.condition_name) = 'light' THEN 0
        WHEN LOWER(t.condition_name) = 'partial' THEN 1
        WHEN LOWER(t.condition_name) = 'deepest' THEN 2
        ELSE NULL
    END AS condition_code,

    -- Geometry features
    geom.total_layout_length,
    geom.max_layout_breadth,
    geom.max_layout_height,
    geom.avg_cross_section,
    geom.sum_bh_sections,
    geom.std_breadth,
    geom.std_height,
    geom.n_frustum_points,

    -- Geometry ratios
    geom.total_layout_length
        / NULLIF(geom.max_layout_breadth, 0) AS length_breadth_ratio,

    geom.max_layout_breadth
        / NULLIF(geom.max_layout_height, 0) AS breadth_height_ratio,

    t.draft
        / NULLIF(geom.max_layout_height, 0) AS draft_height_ratio,

    t.vcg
        / NULLIF(geom.max_layout_height, 0) AS vcg_height_ratio,

    t.displacement
        / NULLIF(geom.total_layout_length, 0) AS displacement_per_length,

    -- Compartment features
    comp_data.total_compartments,
    comp_data.total_subcompartments,
    comp_data.avg_permeability,
    comp_data.min_permeability,
    comp_data.max_permeability,

    comp_data.avg_compartment_length,
    comp_data.max_compartment_length,
    comp_data.std_compartment_length,
    comp_data.avg_compartment_cross_section,
    comp_data.max_compartment_cross_section,
    comp_data.largest_length_ratio,
    comp_data.largest_cross_section_ratio,

    comp_data.n_compartments_aft,
    comp_data.n_compartments_mid,
    comp_data.n_compartments_forward,

    comp_data.avg_perm_aft,
    comp_data.avg_perm_mid,
    comp_data.avg_perm_forward,

    -- Content features
    comp_data.n_cargo,
    comp_data.n_fuel_oil,
    comp_data.n_gas_oil,
    comp_data.n_potable_water,
    comp_data.n_ballast,
    comp_data.n_void,
    comp_data.n_cargohold_hatch,

    -- Content by region
    comp_data.n_cargo_aft,
    comp_data.n_cargo_mid,
    comp_data.n_cargo_forward,

    comp_data.n_ballast_aft,
    comp_data.n_ballast_mid,
    comp_data.n_ballast_forward,

    comp_data.n_void_aft,
    comp_data.n_void_mid,
    comp_data.n_void_forward,

    -- Opening features
    opening_data.total_openings,
    opening_data.openings_per_compartment,
    opening_data.avg_opening_height,
    opening_data.max_opening_height,
    opening_data.avg_opening_area,
    opening_data.max_opening_area,

    opening_data.n_openings_aft,
    opening_data.n_openings_mid,
    opening_data.n_openings_forward,

    opening_data.n_openings_low,
    opening_data.n_openings_middle_height,
    opening_data.n_openings_high,

    -- Density / ratio features
    comp_data.total_compartments
        / NULLIF(geom.total_layout_length, 0) AS compartments_per_length,

    opening_data.total_openings
        / NULLIF(geom.total_layout_length, 0) AS openings_per_length,

    comp_data.n_ballast * 1.0
        / NULLIF(comp_data.total_compartments, 0) AS ballast_ratio,

    comp_data.n_void * 1.0
        / NULLIF(comp_data.total_compartments, 0) AS void_ratio,

    comp_data.n_cargo * 1.0
        / NULLIF(comp_data.total_compartments, 0) AS cargo_ratio,

    -- Targets
    t.attained_index AS target_attained_index,

    (t.attained_index - t.required_index) AS target_margin

FROM trim_gm t

JOIN ship_version sv
    ON sv.id = t.ship_version_id

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
    t.ship_version_id;
"""


def test_entire_table_queries(conn):
    print(pd.read_sql("SELECT COUNT(*) FROM trim_gm", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM compartment", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM subcompartment", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM subcompartment_shape", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM frustum_point", conn))


def test_ctes_query(conn):
    print(
        pd.read_sql(
            """
            WITH comp_data AS (
                SELECT
                    comp.ship_version_id,
                    COUNT(DISTINCT comp.id) AS total_compartments,
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
                    COUNT(*) AS n
                FROM subcompartment_shape ss
                JOIN subcompartment sub
                    ON sub.shape_guid = ss.shape_guid
                JOIN frustum_point fp
                    ON fp.subcompartment_shape_id = ss.id
                GROUP BY ss.ship_version_id
            )
            SELECT * FROM geom
            """,
            conn,
        )
    )


# Perform test queries.
test_entire_table_queries(conn)
test_ctes_query(conn)
test_geom_query(conn)

# Execute query and load into DataFrame
df = pd.read_sql_query(query, conn)

# Show results
print(df.head())

# Optional: save results
df.to_csv("data/all_ships_partial_v5.csv", index=False)

# Close connection
conn.close()