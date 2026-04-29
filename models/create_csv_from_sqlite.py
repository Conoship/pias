import sqlite3
import pandas as pd

# Connect to SQLite database
conn = sqlite3.connect("../utils/localhost.db")

query = """
WITH comp_data AS (
    SELECT
        comp.ship_version_id,
        COUNT(DISTINCT comp.id) AS total_compartments,
        AVG(sub.permeability_for_damage_stability) AS avg_permeability,
        CAST(COUNT(DISTINCT op.id) AS REAL) /
            NULLIF(COUNT(DISTINCT comp.id), 0) AS openings_per_compartment,

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
    LEFT JOIN opening op
        ON op.compartment_id = comp.id
    GROUP BY comp.ship_version_id
),

geom AS (
    SELECT
        ss.ship_version_id,
        MAX(fp.L) - MIN(fp.L) AS total_layout_length,
        MAX(fp.B) AS max_layout_breadth,
        MAX(fp.H) AS max_layout_height,
        AVG(fp.B * fp.H) AS avg_cross_section,
        SUM(fp.B * fp.H) AS sum_bh_sections,

        -- Manual stddev calculation for SQLite
        SQRT(AVG(fp.B * fp.B) - AVG(fp.B) * AVG(fp.B)) AS std_breadth,
        SQRT(AVG(fp.H * fp.H) - AVG(fp.H) * AVG(fp.H)) AS std_height,

        COUNT(*) AS n_frustum_points

    FROM subcompartment_shape ss
    JOIN subcompartment sub
        ON sub.shape_guid = ss.shape_guid
    JOIN compartment comp
        ON comp.id = sub.compartment_id
    JOIN frustum_point fp
        ON fp.subcompartment_shape_id = ss.id
    GROUP BY ss.ship_version_id
)

SELECT
    t.ship_version_id,
    sv.ship_id,
    t.draft,
    t.trim,
    t.mg,
    t.displacement,
    t.vcg,

    CASE
        WHEN LOWER(t.condition_name) = 'light' THEN 0
        WHEN LOWER(t.condition_name) = 'partial' THEN 1
        WHEN LOWER(t.condition_name) = 'deepest' THEN 2
        ELSE NULL
    END AS condition_code,

    comp_data.total_compartments,
    comp_data.avg_permeability,
    comp_data.openings_per_compartment,
    comp_data.n_cargo,
    comp_data.n_fuel_oil,
    comp_data.n_gas_oil,
    comp_data.n_potable_water,
    comp_data.n_ballast,
    comp_data.n_void,
    comp_data.n_cargohold_hatch,

    geom.total_layout_length,
    geom.max_layout_breadth,
    geom.max_layout_height,
    geom.avg_cross_section,
    geom.sum_bh_sections,
    geom.std_breadth,
    geom.std_height,
    geom.n_frustum_points,

    t.attained_index AS target_attained_index,
    (t.attained_index - t.required_index) AS target_margin

FROM trim_gm t
JOIN ship_version sv
    ON sv.id = t.ship_version_id
LEFT JOIN comp_data
    ON comp_data.ship_version_id = t.ship_version_id
LEFT JOIN geom
    ON geom.ship_version_id = t.ship_version_id

WHERE comp_data.avg_permeability IS NOT NULL
    AND comp_data.total_compartments IS NOT NULL
    AND t.attained_index IS NOT NULL

ORDER BY
    t.ship_version_id,
    condition_code;
"""

def test_entire_table_queries(conn):
    print(pd.read_sql("SELECT COUNT(*) FROM trim_gm", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM compartment", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM subcompartment", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM subcompartment_shape", conn))
    print(pd.read_sql("SELECT COUNT(*) FROM frustum_point", conn))

def test_ctes_query(conn):
    print(pd.read_sql("""
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
    """, conn))

def test_geom_query(conn):
    print(pd.read_sql("""
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
    """, conn))

# Perform test queries.
test_entire_table_queries(conn)
test_ctes_query(conn)
test_geom_query(conn)

# Execute query and load into DataFrame
df = pd.read_sql_query(query, conn)

# Show results
print(df.head())

# Optional: save results
df.to_csv("../../../data/all_ships_all_conditions_v4.csv", index=False)

# Close connection
conn.close()
