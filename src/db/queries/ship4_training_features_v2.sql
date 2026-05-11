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
	comp_data.total_compartments,
	c.subdivision_length,
	c.complies::int AS complies_boolean,
	comp_data.avg_permeability,
	(c.attained_index - c.required_index) AS target_margin
FROM public.trim_gm t
	JOIN public.probdam_conclusion c ON c.ship_version_id = t.ship_version_id
	LEFT JOIN (
		SELECT comp.ship_version_id,
			COUNT(DISTINCT comp.id) AS total_compartments,
			AVG(sub.permeability_for_damage_stability) as avg_permeability
		FROM public.compartment comp
			JOIN public.subcompartment sub ON sub.compartment_id = comp.id
		GROUP BY comp.ship_version_id
	) comp_data ON comp_data.ship_version_id = t.ship_version_id
WHERE t.ship_version_id BETWEEN 499 AND 538
	AND comp_data.avg_permeability IS NOT NULL
	AND comp_data.total_compartments IS NOT NULL
ORDER BY t.ship_version_id;