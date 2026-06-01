# Import standard library packages.
import ast
import math
import pickle
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable, Protocol, cast

# Import third party packages.
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox, QWidget

# Import local packages.
from src.db.db import create_all_tables
from src.models.random_forest_baseline import RandomForestBaseline


class _FeatureEngineer(Protocol):
    def __call__(self, X: pd.DataFrame) -> pd.DataFrame: ...


class _IntervalPredictor(Protocol):
    def predict_interval(self, X: pd.DataFrame) -> tuple[Any, Any]: ...


class _TreeEstimator(Protocol):
    def predict(self, X: Any) -> Any: ...


class _ForestPredictor(Protocol):
    estimators_: list[_TreeEstimator]


class _ModelUnpickler(pickle.Unpickler):
    """
    Unpickler that maps legacy model pickles created from script execution.
    """

    def find_class(self, module: str, name: str) -> object:
        if module == "__main__" and name == "RandomForestBaseline":
            return RandomForestBaseline

        return super().find_class(module, name)


def _is_missing(value: Any) -> bool:
    return bool(pd.isna(value) or (isinstance(value, str) and value.strip() == ""))


def _first_value(df: pd.DataFrame, column: str, default: Any = None) -> Any:
    if column not in df.columns:
        return default

    values = df[column].dropna()
    if values.empty:
        return default

    return values.iloc[0]


def _insert_ship_data(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    ship_name = str(_first_value(df, "ship", _first_value(df, "name", "unknownship")))
    design_name = str(_first_value(df, "design_name", "unknowndesign"))
    version = str(_first_value(df, "version", "unknownversion"))
    subversion = str(_first_value(df, "subversion", ""))
    ship_run = str(_first_value(df, "ship_run", ""))

    cur = conn.cursor()
    cur.execute("INSERT INTO ship (name) VALUES (?)", (ship_name,))
    ship_id = cur.lastrowid
    if ship_id is None:
        raise ValueError("Could not insert ship row.")

    cur.execute(
        """
        INSERT INTO ship_version
            (ship_id, design_name, version, subversion, ship_run)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ship_id, design_name, version, subversion, ship_run),
    )
    ship_version_id = cur.lastrowid
    if ship_version_id is None:
        raise ValueError("Could not insert ship version row.")

    cur.execute(
        """
        INSERT INTO main_dimensions
            (ship_version_id, lpp, loa, breadth, depth)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            ship_version_id,
            _first_value(df, "lpp"),
            _first_value(df, "loa"),
            _first_value(df, "breadth"),
            _first_value(df, "depth"),
        ),
    )

    conn.commit()
    return ship_version_id


def _insert_layout_data(
    conn: sqlite3.Connection, df: pd.DataFrame, ship_version_id: int
) -> None:
    cur = conn.cursor()

    content_rows = df[df["record_type"] == "content_category"]
    for _, row in content_rows.iterrows():
        content_id = row["design_content_id_number"]
        name = row["content_category_name"]
        if _is_missing(content_id) or _is_missing(name):
            continue

        cur.execute(
            """
            INSERT OR IGNORE INTO content_category
                (design_content_id_number, name)
            VALUES (?, ?)
            """,
            (int(content_id), str(name)),
        )

    shape_ids: dict[str, int] = {}
    shape_rows = df[df["record_type"] == "subcompartment_shape"]
    for _, row in shape_rows.iterrows():
        shape_guid = row["shape_guid"]
        if _is_missing(shape_guid):
            continue

        cur.execute(
            """
            INSERT INTO subcompartment_shape
                (ship_version_id, shape_guid, side)
            VALUES (?, ?, ?)
            """,
            (ship_version_id, str(shape_guid), row["side"]),
        )
        shape_id = cur.lastrowid
        if shape_id is None:
            raise ValueError("Could not insert subcompartment shape row.")
        shape_ids[str(shape_guid)] = shape_id

    frustum_rows = df[df["record_type"] == "frustum_point"]
    for _, row in frustum_rows.iterrows():
        shape_guid = str(row["shape_guid"])
        shape_id = shape_ids.get(shape_guid)
        if shape_id is None:
            continue

        cur.execute(
            """
            INSERT INTO frustum_point
                (subcompartment_shape_id, aftfwd_and_num, L, B, H)
            VALUES (?, ?, ?, ?, ?)
            """,
            (shape_id, row["aftfwd_and_num"], row["L"], row["B"], row["H"]),
        )

    compartment_ids: dict[str, int] = {}
    compartment_rows = df[df["record_type"] == "compartment"]
    for _, row in compartment_rows.iterrows():
        xml_guid = row["xml_compartment_guid"]
        if _is_missing(xml_guid):
            continue

        cur.execute(
            """
            INSERT INTO compartment
                (ship_version_id,
                    xml_comparment_id,
                    xml_compartment_guid,
                    name,
                    selected_for_output,
                    design_content_id_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ship_version_id,
                row["xml_compartment_id"],
                str(xml_guid),
                (
                    row["compartment_name"]
                    if not _is_missing(row["compartment_name"])
                    else ""
                ),
                int(bool(row["selected_for_output"])),
                row["design_content_id_number"],
            ),
        )
        compartment_id = cur.lastrowid
        if compartment_id is None:
            raise ValueError("Could not insert compartment row.")
        compartment_ids[str(xml_guid)] = compartment_id

    subcompartment_rows = df[df["record_type"] == "subcompartment"]
    for _, row in subcompartment_rows.iterrows():
        compartment_id = compartment_ids.get(str(row["xml_compartment_guid"]))
        if compartment_id is None:
            continue

        cur.execute(
            """
            INSERT INTO subcompartment
                (compartment_id,
                    shape_guid,
                    subcompartment_guid,
                    sign,
                    permeability_for_damage_stability,
                    is_pipe)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                compartment_id,
                row["shape_guid"],
                row["subcompartment_guid"],
                row["sign"],
                row["permeability_for_damage_stability"],
                int(bool(row["is_pipe"])),
            ),
        )

    opening_rows = df[df["record_type"] == "opening"]
    for _, row in opening_rows.iterrows():
        compartment_id = compartment_ids.get(str(row["xml_compartment_guid"]))

        cur.execute(
            """
            INSERT INTO opening
                (ship_version_id,
                    compartment_id,
                    description,
                    opening_type,
                    L, B, H)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ship_version_id,
                compartment_id,
                (
                    row["opening_description"]
                    if not _is_missing(row["opening_description"])
                    else ""
                ),
                row["opening_type"] if not _is_missing(row["opening_type"]) else "",
                row["L"],
                row["B"],
                row["H"],
            ),
        )

    conn.commit()


def _insert_loading_data(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    ship_version_id: int,
    required_index: float,
) -> None:
    cur = conn.cursor()
    loading_rows = [
        (
            "light",
            _first_value(df, "Light Service Draft"),
            _first_value(df, "Light GM Value"),
        ),
        (
            "partial",
            _first_value(
                df, "Partial Subdivision", _first_value(df, "Subdivision Draft")
            ),
            _first_value(df, "Partial GM Value"),
        ),
        (
            "deepest",
            _first_value(df, "Subdivision Draft"),
            _first_value(df, "Deep GM Value"),
        ),
    ]

    for condition_name, draft, mg in loading_rows:
        cur.execute(
            """
            INSERT INTO trim_gm
                (ship_version_id,
                    condition_name,
                    draft,
                    trim,
                    vcg,
                    mg,
                    displacement,
                    attained_index,
                    required_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ship_version_id,
                condition_name,
                draft,
                _first_value(df, "trim"),
                _first_value(df, "vcg"),
                mg,
                _first_value(df, "displacement"),
                0.0,
                required_index,
            ),
        )

    conn.commit()


def _build_feature_database(
    df: pd.DataFrame, required_index: float
) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.create_function("SQRT", 1, math.sqrt)
    create_all_tables(conn)

    ship_version_id = _insert_ship_data(conn, df)
    _insert_layout_data(conn, df, ship_version_id)
    _insert_loading_data(conn, df, ship_version_id, required_index)

    return conn


def _extract_feature_query(script_path: Path) -> str:
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        has_query_target = any(
            isinstance(target, ast.Name) and target.id == "query"
            for target in node.targets
        )
        if has_query_target and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                return node.value.value

    namespace = _load_feature_script_namespace(script_path)
    imported_query = namespace.get("query")
    if isinstance(imported_query, str):
        return imported_query

    raise ValueError(f"No query string found in {script_path}.")


def _feature_script_version(script_path: Path) -> int:
    match = re.search(r"create_csv_v(\d+)\.py$", script_path.name)
    return int(match.group(1)) if match else -1


def _load_feature_script_namespace(script_path: Path) -> dict[str, Any]:
    tree = ast.parse(script_path.read_text(encoding="utf-8"))

    def is_safe_assignment(node: ast.AST) -> bool:
        if not isinstance(node, ast.Assign):
            return False

        try:
            ast.literal_eval(node.value)
        except (SyntaxError, TypeError, ValueError):
            return False

        return True

    allowed_nodes = [
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.FunctionDef,
                ast.ClassDef,
            ),
        )
        or is_safe_assignment(node)
    ]
    module = ast.Module(body=allowed_nodes, type_ignores=[])
    ast.fix_missing_locations(module)

    namespace: dict[str, Any] = {"__file__": str(script_path)}
    exec(compile(module, str(script_path), "exec"), namespace)
    return namespace


def _run_feature_script_query(
    conn: sqlite3.Connection, script_path: Path
) -> pd.DataFrame:
    query = _extract_feature_query(script_path)
    features_df = pd.read_sql_query(query, conn)

    namespace = _load_feature_script_namespace(script_path)
    volume_builder = namespace.get("derive_compartment_volume_by_type")
    if callable(volume_builder):
        volume_features = cast(
            Callable[[sqlite3.Connection], pd.DataFrame], volume_builder
        )(conn)
        features_df = features_df.merge(
            volume_features, on="ship_version_id", how="left"
        )

    return features_df


def _prepare_model_features(
    df: pd.DataFrame, required_index: float, feature_cols: list[str]
) -> pd.DataFrame:
    conn = _build_feature_database(df, required_index)

    try:
        scripts_dir = Path("scripts")
        script_paths = sorted(
            scripts_dir.glob("create_csv*.py"),
            key=_feature_script_version,
            reverse=True,
        )

        errors = []
        for script_path in script_paths:
            try:
                features_df = _run_feature_script_query(conn, script_path)
            except Exception as error:
                errors.append(f"{script_path.name}: {error}")
                continue

            missing_cols = [
                col for col in feature_cols if col not in features_df.columns
            ]
            if missing_cols:
                errors.append(
                    f"{script_path.name}: missing columns {', '.join(missing_cols)}"
                )
                continue

            return features_df

        raise ValueError(
            "Could not find a compatible feature query script for the saved model. "
            f"Checked: {'; '.join(errors)}"
        )

    finally:
        conn.close()


def run_agent_pipeline(
    window: QWidget, required_index: float, df: pd.DataFrame
) -> tuple[list[float], list[tuple[float, float]], list[str]] | None:
    """
    Execute the AI agent pipeline: load data, run the trained model,
    and return the predicted results.

    Args:
        window (QWidget):
            The main application window.

        required_index (float):
            The Required Index (R) value required for the ship to pass according to the SOLAS requirements.

        df_final (pd.DataFrame):
            The df containing the the concatened data frames from the other parsers and the user defined values.

    Returns:
        tuple[list[float], list[tuple[float, float]], list[str]]:
            A tuple containing the lists of predictions, 95% CIs and the A against R comparison result (one element per loading condition)
    """
    # Load the model.
    try:
        with open("models/model.pkl", "rb") as file:
            saved = _ModelUnpickler(file).load()

    except FileNotFoundError:
        QMessageBox.warning(
            window,
            "File not found",
            "The ML model .pkl file could not be found.",
        )
        return

    except (AttributeError, EOFError, pickle.UnpicklingError) as error:
        QMessageBox.warning(
            window,
            "Invalid model file",
            f"The ML model .pkl file could not be loaded: {error}",
        )
        return

    saved_model = cast(dict[str, Any], saved)
    model_type = str(saved_model["model_type"])
    model = saved_model["model"]
    feature_cols = cast(list[str], saved_model["feature_cols"])
    engineer_features = cast(
        _FeatureEngineer | None, saved_model.get("engineer_features")
    )

    try:
        features_df = _prepare_model_features(df, required_index, feature_cols)

    except Exception as error:
        QMessageBox.warning(
            window,
            "Feature generation failed",
            str(error),
        )
        return

    # Keep the exact model feature columns and coerce them to numeric. Some SQL
    # features can come back as object dtype when their values are NULL.
    X = features_df.copy()
    for col in feature_cols:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    # Split the data into each loading condition so we can get model output for each loading condition.
    if "condition_code" in X.columns:
        X = (
            X[X["condition_code"].isin([0, 1, 2])]
            .sort_values("condition_code")
            .drop_duplicates("condition_code", keep="first")
        )
    else:
        X = X.head(3)

    if engineer_features is not None:
        X = engineer_features(X)

    X = X[feature_cols]
    print("=========================")
    print("Original DataFrame Given:")
    print(df)
    print("=========================")
    print("Engineered Features based on the DataFrame:")
    print(X)
    print("=========================")

    # Predict based on the model type - once a single performing model is selected, this can be narrowed down.
    predictions: list[float] = []
    confidence_intevals: list[tuple[float, float]] = []
    if model_type == "MAPIE XGB Regressor":
        interval_model = cast(_IntervalPredictor, model)
        model_predictions, intervals = interval_model.predict_interval(X)
        predictions = [float(prediction) for prediction in model_predictions.ravel()]
        confidence_intevals = [
            (float(lower), float(upper)) for lower, upper in intervals[:, :, 0]
        ]

    else:
        # Get per-tree predictions and calculate the 95% CI to display confidence.
        forest_model = cast(_ForestPredictor, model)
        X_values = X.to_numpy()
        all_tree_preds = np.array(
            [tree.predict(X_values) for tree in forest_model.estimators_]
        )
        predictions = [
            float(prediction) for prediction in np.mean(all_tree_preds, axis=0)
        ]
        lower_bounds = np.percentile(all_tree_preds, 2.5, axis=0)
        upper_bounds = np.percentile(all_tree_preds, 97.5, axis=0)
        confidence_intevals = [
            (float(lower), float(upper))
            for lower, upper in zip(lower_bounds, upper_bounds)
        ]

    # Get the pass results for each prediction, for each loading condition.
    # The minimum value for each condition is 0.5 * R.
    pass_results = [
        "Pass" if prediction >= required_index * 0.5 else "Fail"
        for prediction in predictions
    ]

    return predictions, confidence_intevals, pass_results
