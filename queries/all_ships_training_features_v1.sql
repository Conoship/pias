WITH comp_data AS (
    SELECT
        comp.ship_version_id,
        COUNT(DISTINCT comp.id)                                             AS total_compartments,
        AVG(sub.permeability_for_damage_stability)                          AS avg_permeability,
        COUNT(DISTINCT op.id) * 1.0 / NULLIF(COUNT(DISTINCT comp.id), 0)   AS openings_per_compartment
    FROM public.compartment comp
    JOIN public.subcompartment sub  ON sub.compartment_id = comp.id
    LEFT JOIN public.opening op     ON op.compartment_id  = comp.id
    GROUP BY comp.ship_version_id
),

geom AS (
    SELECT
        ss.ship_version_id,
        MAX(fp.L) - MIN(fp.L)       AS total_layout_length,
        MAX(fp.B)                   AS max_layout_breadth,
        MAX(fp.H)                   AS max_layout_height,
        AVG(fp.B * fp.H)            AS avg_cross_section,
        SUM(fp.B * fp.H)            AS sum_bh_sections,
        STDDEV(fp.B)                AS std_breadth,
        STDDEV(fp.H)                AS std_height,
        COUNT(*)                    AS n_frustum_points
    FROM public.subcompartment_shape ss
    JOIN public.subcompartment sub  ON sub.shape_guid             = ss.shape_guid
    JOIN public.compartment comp    ON comp.id                    = sub.compartment_id
    JOIN public.frustum_point fp    ON fp.subcompartment_shape_id = ss.id
    GROUP BY ss.ship_version_id
),

conclusion AS (
    SELECT DISTINCT ON (ship_version_id)
        ship_version_id,
        subdivision_length,
        required_index,
        attained_index
    FROM public.probdam_conclusion
    ORDER BY ship_version_id
)

SELECT
    t.ship_version_id,
    t.draft,
    t.trim,
    t.mg,
    t.displacement,
    t.vcg,
    CASE
        WHEN LOWER(t.condition_name) = 'light'   THEN 0
        WHEN LOWER(t.condition_name) = 'partial'  THEN 1
        WHEN LOWER(t.condition_name) = 'deepest'  THEN 2
        ELSE NULL
    END                                         AS condition_code,
    comp_data.total_compartments,
    comp_data.avg_permeability,
    comp_data.openings_per_compartment,
    c.subdivision_length,
    geom.total_layout_length,
    geom.max_layout_breadth,
    geom.max_layout_height,
    geom.avg_cross_section,
    geom.sum_bh_sections,
    geom.std_breadth,
    geom.std_height,
    geom.n_frustum_points,
    c.attained_index                            AS target_attained_index,
    (c.attained_index - c.required_index)       AS target_margin

FROM public.trim_gm t
JOIN conclusion c       ON c.ship_version_id        = t.ship_version_id
LEFT JOIN comp_data     ON comp_data.ship_version_id = t.ship_version_id
LEFT JOIN geom          ON geom.ship_version_id      = t.ship_version_id

WHERE comp_data.avg_permeability   IS NOT NULL
  AND comp_data.total_compartments IS NOT NULL
ORDER BY t.ship_version_id, condition_code;