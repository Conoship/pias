SELECT t.ship_version_id,
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
    comp_data.openings_per_compartment,
    comp_data.total_compartments,
    c.subdivision_length,
    comp_data.avg_permeability,
    -- Choose one of these as your target:
    c.attained_index AS target_attained_index,
    (c.attained_index - c.required_index) AS target_margin
FROM public.trim_gm t
    JOIN (
        SELECT DISTINCT ON (ship_version_id) ship_version_id,
            subdivision_length,
            required_index,
            attained_index
        FROM public.probdam_conclusion
        ORDER BY ship_version_id
    ) c ON c.ship_version_id = t.ship_version_id
    LEFT JOIN (
        SELECT comp.ship_version_id,
            COUNT(DISTINCT comp.id) AS total_compartments,
            AVG(sub.permeability_for_damage_stability) AS avg_permeability,
            COUNT(DISTINCT op.id) * 1.0 / NULLIF(COUNT(DISTINCT comp.id), 0) AS openings_per_compartment
        FROM public.compartment comp
            JOIN public.subcompartment sub ON sub.compartment_id = comp.id
            LEFT JOIN public.opening op ON op.compartment_id = comp.id
        GROUP BY comp.ship_version_id
    ) comp_data ON comp_data.ship_version_id = t.ship_version_id
WHERE comp_data.avg_permeability IS NOT NULL
    AND comp_data.total_compartments IS NOT NULL
ORDER BY t.ship_version_id;