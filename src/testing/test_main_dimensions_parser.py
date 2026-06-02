# Import third party packages.
import pandas as pd
import pytest
from unittest.mock import patch

# Import local packages.
from src.app.parsers.main_dimensions_parser import MainDimensionsParser


class TestInit:
    _EXPECTED_COLS = [
        "Project Name",
        "Length between perpendiculars",
        "Length overall",
        "Moulded breadth",
        "Moulded depth",
    ]

    def test_class_instantiates(self):
        parser = MainDimensionsParser()
        assert parser is not None

    def test_parser_has_attribute_df(self):
        parser = MainDimensionsParser()
        assert hasattr(parser, "_df")

    def test_parser_has_attribute_cols(self):
        parser = MainDimensionsParser()
        assert hasattr(parser, "_cols")

    def test_parser_has_correct_columns(self):
        parser = MainDimensionsParser()
        assert parser.get_cols() == self._EXPECTED_COLS


class TestExtractFieldValue:
    def test_existing_field_value(self):
        pass

    def test_non_existing_field_value(self):
        pass

    def test_less_braces_than_required(self):
        pass


class TestExtractProjectName:
    def test_empty_string(self):
        pass

    def test_valid_string(self):
        pass

    def test_single_letter_project_name(self):
        pass

    def test_very_large_project_name(self):
        pass

    def test_project_name_contains_special_characters(self):
        pass

    def test_string_with_no_project_name_regex(self):
        pass

    def test_string_with_no_project_name_value(self):
        pass


class TestParseFloat:
    def test_valid_float(self):
        pass

    def test_invalid_float(self):
        pass

    def test_float_with_comma(self):
        pass


class TestValidateDf:
    def test_valid_df(self):
        pass

    def test_single_column_from_accepted_missing_df(self):
        pass

    def test_multiple_columns_from_accepted_missing_df(self):
        pass

    def test_single_column_not_from_accepted_missing_df(self):
        pass

    def test_multiple_columns_not_from_accepted_missing_df(self):
        pass


class TestParseFile:
    pass
