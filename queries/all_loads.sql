WITH comp_data AS (
    SELECT comp.ship_version_id,
        COUNT(DISTINCT comp.id) AS total_compartments,
        AVG(sub.permeability_for_damage_stability) AS avg_permeability,
        COUNT(DISTINCT op.id) * 1.0 / NULLIF(COUNT(DISTINCT comp.id), 0) AS openings_per_compartment,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 1
        ) AS n_cargo,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 2
        ) AS n_fuel_oil,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 3
        ) AS n_gas_oil,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 4
        ) AS n_potable_water,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 6
        ) AS n_ballast,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 8
        ) AS n_void,
        COUNT(DISTINCT comp.id) FILTER (
            WHERE comp.design_content_id_number = 12
        ) AS n_cargohold_hatch
    FROM public.compartment comp
        JOIN public.subcompartment sub ON sub.compartment_id = comp.id
        LEFT JOIN public.opening op ON op.compartment_id = comp.id
    GROUP BY comp.ship_version_id
),
geom AS (
    SELECT ss.ship_version_id,
        MAX(fp.L) - MIN(fp.L) AS total_layout_length,
        MAX(fp.B) AS max_layout_breadth,
        MAX(fp.H) AS max_layout_height,
        AVG(fp.B * fp.H) AS avg_cross_section,
        SUM(fp.B * fp.H) AS sum_bh_sections,
        STDDEV(fp.B) AS std_breadth,
        STDDEV(fp.H) AS std_height,
        COUNT(*) AS n_frustum_points
    FROM public.subcompartment_shape ss
        JOIN public.subcompartment sub ON sub.shape_guid = ss.shape_guid
        JOIN public.compartment comp ON comp.id = sub.compartment_id
        JOIN public.frustum_point fp ON fp.subcompartment_shape_id = ss.id
    GROUP BY ss.ship_version_id
)
SELECT t.ship_version_id,
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
FROM public.trim_gm t
    JOIN public.ship_version sv ON sv.id = t.ship_version_id
    LEFT JOIN comp_data ON comp_data.ship_version_id = t.ship_version_id
    LEFT JOIN geom ON geom.ship_version_id = t.ship_version_id
WHERE comp_data.avg_permeability IS NOT NULL
    AND comp_data.total_compartments IS NOT NULL
    AND t.attained_index IS NOT NULL
ORDER BY t.ship_version_id,
    condition_code;