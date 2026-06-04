import pandas as pd


OPENING_FEATURE_COLUMNS = [
    "n_openings",
    "min_opening_h_over_depth",
    "mean_opening_h_over_depth",
    "mean_opening_abs_b_over_half_breadth",
    "max_opening_abs_b_over_half_breadth",
    "mean_opening_endness",
    "max_opening_endness",
    "mean_opening_risk_index",
    "max_opening_risk_index",
    "high_risk_opening_ratio",
    "area_weighted_opening_risk",
    "max_area_weighted_opening_risk",
    "n_high_risk_openings",
    "low_outboard_opening_ratio",
    "end_low_outboard_opening_ratio",
]


def read_openings_for_ship_versions(conn, ship_version_ids):
    """
    Read all openings for the given ship versions from the database.
    """
    ship_version_ids = [int(ship_id) for ship_id in ship_version_ids]

    if len(ship_version_ids) == 0:
        return pd.DataFrame()

    question_marks = ", ".join(["?"] * len(ship_version_ids))

    query = f"""
        WITH ship_bounds AS (
            SELECT
                ss.ship_version_id,
                MIN(fp.L) AS ship_min_l,
                MAX(fp.L) - MIN(fp.L) AS total_layout_length,
                MAX(ABS(fp.B)) AS max_abs_b,
                MAX(fp.H) AS max_h
            FROM subcompartment_shape ss
            JOIN frustum_point fp
                ON fp.subcompartment_shape_id = ss.id
            WHERE fp.L IS NOT NULL
              AND ss.ship_version_id IN ({question_marks})
            GROUP BY ss.ship_version_id
        ),

        main_dimensions_by_ship AS (
            SELECT
                sv.ship_id,
                AVG(md.breadth) AS breadth,
                AVG(md.depth) AS depth
            FROM main_dimensions md
            JOIN ship_version sv
                ON sv.id = md.ship_version_id
            GROUP BY sv.ship_id
        )

        SELECT
            op.ship_version_id,
            op.length,
            op.breadth AS opening_breadth,
            op.L,
            op.B,
            op.H,
            COALESCE(md.breadth, 2.0 * sb.max_abs_b) AS ship_breadth,
            COALESCE(md.depth, sb.max_h) AS depth,
            sb.ship_min_l,
            sb.total_layout_length
        FROM opening op
        JOIN ship_version sv
            ON sv.id = op.ship_version_id
        LEFT JOIN main_dimensions_by_ship md
            ON md.ship_id = sv.ship_id
        LEFT JOIN ship_bounds sb
            ON sb.ship_version_id = op.ship_version_id
        WHERE op.ship_version_id IN ({question_marks})
    """

    params = ship_version_ids + ship_version_ids
    return pd.read_sql_query(query, conn, params=params)


def calculate_opening_risk_features(openings):
    """
    Calculate opening risk features for each ship version.
    """
    if openings.empty:
        return pd.DataFrame(columns=["ship_version_id"] + OPENING_FEATURE_COLUMNS)

    df = openings.copy()

    # Normalize opening position by ship size.
    df["h_ratio"] = pd.to_numeric(df["H"], errors="coerce") / pd.to_numeric(
        df["depth"],
        errors="coerce",
    )
    df["b_ratio"] = pd.to_numeric(df["B"], errors="coerce").abs() / (
        pd.to_numeric(df["ship_breadth"], errors="coerce") / 2.0
    )
    df["l_ratio"] = (
        pd.to_numeric(df["L"], errors="coerce")
        - pd.to_numeric(df["ship_min_l"], errors="coerce")
    ) / pd.to_numeric(df["total_layout_length"], errors="coerce")

    # Openings are riskier when they are low, outboard, and near aft/fwd ends.
    df["endness"] = ((df["l_ratio"].clip(0.0, 1.0) - 0.5).abs() * 2.0)
    df["risk"] = (
        (1.0 - df["h_ratio"].clip(0.0, 1.0))
        * df["b_ratio"].clip(0.0, 1.0)
        * (0.5 + 0.5 * df["endness"])
    )

    # Use opening area as weight. If area is missing, count all openings equally.
    df["area"] = (
        pd.to_numeric(df["length"], errors="coerce")
        * pd.to_numeric(df["opening_breadth"], errors="coerce")
    ).fillna(0.0)

    if df["area"].sum() == 0:
        df["area"] = 1.0

    df["weighted_risk"] = df["area"] * df["risk"]
    df["high_risk"] = df["risk"] >= 0.25
    df["low_outboard"] = (df["h_ratio"] <= 0.35) & (df["b_ratio"] >= 0.70)
    df["end_low_outboard"] = df["low_outboard"] & (df["endness"] >= 0.70)

    rows = []

    # Make one final feature row per ship version.
    for ship_version_id, group in df.groupby("ship_version_id"):
        total_area = group["area"].sum()

        rows.append(
            {
                "ship_version_id": ship_version_id,
                "n_openings": len(group),
                "min_opening_h_over_depth": group["h_ratio"].min(),
                "mean_opening_h_over_depth": group["h_ratio"].mean(),
                "mean_opening_abs_b_over_half_breadth": group["b_ratio"].mean(),
                "max_opening_abs_b_over_half_breadth": group["b_ratio"].max(),
                "mean_opening_endness": group["endness"].mean(),
                "max_opening_endness": group["endness"].max(),
                "mean_opening_risk_index": group["risk"].mean(),
                "max_opening_risk_index": group["risk"].max(),
                "high_risk_opening_ratio": group["high_risk"].mean(),
                "area_weighted_opening_risk": group["weighted_risk"].sum()
                / total_area,
                "max_area_weighted_opening_risk": group["weighted_risk"].max()
                / total_area,
                "n_high_risk_openings": group["high_risk"].sum(),
                "low_outboard_opening_ratio": group["low_outboard"].mean(),
                "end_low_outboard_opening_ratio": group["end_low_outboard"].mean(),
            }
        )

    return pd.DataFrame(rows).fillna(0.0)


def derive_opening_risk_features(conn, ship_version_ids=None):
    """
    Main function used by CSV v3 to add opening risk features.
    """
    if ship_version_ids is None:
        query = "SELECT DISTINCT ship_version_id FROM opening ORDER BY ship_version_id"
        ship_ids = pd.read_sql_query(query, conn)
        ship_version_ids = ship_ids["ship_version_id"].dropna().astype(int).tolist()
    else:
        ship_version_ids = [int(ship_id) for ship_id in ship_version_ids]

    base = pd.DataFrame({"ship_version_id": ship_version_ids})
    openings = read_openings_for_ship_versions(conn, ship_version_ids)
    features = calculate_opening_risk_features(openings)

    result = base.merge(features, on="ship_version_id", how="left")
    result[OPENING_FEATURE_COLUMNS] = result[OPENING_FEATURE_COLUMNS].fillna(0.0)

    return result
