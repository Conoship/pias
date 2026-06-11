import pandas as pd
import yaml

from src.resources import resource_path

FEATURES_PATH = resource_path("src/models/features.yaml")
DEFAULT_FEATURE_SET = "volume_ratios"


def select_feature_columns(
    df: pd.DataFrame,
    feature_set_name: str = DEFAULT_FEATURE_SET,
    fallback_features: list[str] | None = None,
    fallback_drop_columns: list[str] | None = None,
) -> list[str]:
    try:
        config = yaml.safe_load(FEATURES_PATH.read_text()) or {}
        features = config["feature_sets"][feature_set_name]

        if all(feature in df.columns for feature in features):
            return features
    except (FileNotFoundError, KeyError, TypeError, yaml.YAMLError):
        pass

    if fallback_features is not None:
        return [feature for feature in fallback_features if feature in df.columns]

    drop_cols = set(fallback_drop_columns or [])
    return [
        col for col in df.select_dtypes(include=["number"]).columns
        if col not in drop_cols
    ]
