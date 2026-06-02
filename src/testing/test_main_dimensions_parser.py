# Import standard library packages.
import builtins

# Import third party packages.
import pandas as pd
import pytest

# Import local packages.
from src.app.parsers.main_dimensions_parser import MainDimensionsParser


def make_parser() -> MainDimensionsParser:
    return MainDimensionsParser()


def rtf_value_line(feature_name: str, value: str) -> str:
    return f"{feature_name} {{label}}{{{value}}}{{m}}\n"


def write_main_dimensions_file(tmp_path, lines: list[str]) -> str:
    file_path = tmp_path / "main_dimensions.rtf"
    file_path.write_text("".join(lines), encoding="utf-8")
    return str(file_path)


def valid_main_dimensions_lines() -> list[str]:
    lines = ["{Project name : TestShip}\n"]
    lines.extend(["ignored before general particulars\n"] * 30)
    lines.append(rtf_value_line("Length between perpendiculars", "120,5"))
    lines.append(rtf_value_line("Length overall", "125.25"))
    lines.append(rtf_value_line("Moulded breadth", "22"))
    lines.append(rtf_value_line("Moulded depth", "8.75"))
    return lines


class TestInit:
    def test_parser_starts_with_expected_columns(self):
        parser = make_parser()
        assert list(parser._df.columns) == [
            "Project Name",
            "Length between perpendiculars",
            "Length overall",
            "Moulded breadth",
            "Moulded depth",
        ]

    def test_parser_starts_with_empty_dataframe(self):
        parser = make_parser()
        assert parser._df.empty


class TestExtractFieldValue:
    def test_extract_field_value_returns_second_braced_value_after_feature(self):
        parser = make_parser()
        line = "prefix {ignore} Length overall {label} { 125.25 } {m}"
        result = parser._extract_field_value(line, "Length overall")
        assert result == "125.25"

    def test_extract_field_value_returns_none_when_feature_is_missing(self):
        parser = make_parser()
        result = parser._extract_field_value(
            "Moulded breadth {label}{22}{m}", "Length overall"
        )
        assert result is None

    def test_extract_field_value_returns_none_when_line_has_too_few_braced_values(self):
        parser = make_parser()
        result = parser._extract_field_value(
            "Length overall {label}{125.25}", "Length overall"
        )
        assert result is None

    def test_extract_field_value_ignores_braces_before_feature_name(self):
        parser = make_parser()
        line = "{before}{also before} Moulded depth {label}{8.75}{m}"
        result = parser._extract_field_value(line, "Moulded depth")
        assert result == "8.75"


class TestExtractProjectName:
    def test_extract_project_name_from_braced_line(self):
        parser = make_parser()
        result = parser._extract_project_name("{Project name : A30333}")
        assert result == "A30333"

    def test_extract_project_name_from_unbraced_line(self):
        parser = make_parser()
        result = parser._extract_project_name("Project name : TestShip ")
        assert result == "TestShip"

    def test_extract_project_name_returns_none_when_missing(self):
        parser = make_parser()
        result = parser._extract_project_name("Length overall {label}{125.25}{m}")
        assert result is None


class TestParseFloat:
    def test_parse_float_accepts_dot_decimal_separator(self):
        parser = make_parser()
        assert parser._parse_float("125.25") == 125.25

    def test_parse_float_accepts_comma_decimal_separator_from_rtf(self):
        parser = make_parser()
        assert parser._parse_float("120,5") == 120.5

    def test_parse_float_raises_for_non_numeric_text(self):
        parser = make_parser()
        with pytest.raises(ValueError):
            parser._parse_float("not a number")


class TestValidateDf:
    def test_validate_df_passes_when_all_required_values_are_present(self):
        parser = make_parser()
        parser._df.loc[0] = ["TestShip", 120.5, 125.25, 22.0, 8.75]
        parser._validate_df()

    def test_validate_df_raises_when_dataframe_is_empty(self):
        parser = make_parser()
        with pytest.raises(Exception, match="RTF Value Missing"):
            parser._validate_df()

    def test_validate_df_raises_when_required_column_is_missing(self):
        parser = make_parser()
        parser._df = pd.DataFrame(
            [{"Project Name": "TestShip", "Length overall": 125.25}]
        )
        with pytest.raises(Exception) as error:
            parser._validate_df()

        message = str(error.value)
        assert "RTF Value Missing" in message
        assert "Length between perpendiculars" in message
        assert "Moulded breadth" in message
        assert "Moulded depth" in message

    def test_validate_df_raises_when_required_values_are_blank_or_nan(self):
        parser = make_parser()
        parser._df.loc[0] = ["TestShip", 120.5, "", pd.NA, 8.75]
        with pytest.raises(Exception) as error:
            parser._validate_df()

        message = str(error.value)
        assert "Length overall" in message
        assert "Moulded breadth" in message

    def test_validate_df_allows_columns_listed_as_accepted_missing(self):
        parser = make_parser()
        parser._ACCEPT_MISSING_COLS = ("Moulded depth",)
        parser._df.loc[0] = ["TestShip", 120.5, 125.25, 22.0, pd.NA]
        parser._validate_df()


class TestParseFile:
    def test_parse_file_returns_renamed_dataframe_with_expected_values(self, tmp_path):
        file_path = write_main_dimensions_file(tmp_path, valid_main_dimensions_lines())
        parser = make_parser()
        result = parser.parse_file(file_path)
        assert list(result.columns) == ["name", "lpp", "loa", "breadth", "depth"]
        assert result.loc[0, "name"] == "TestShip"
        assert result.loc[0, "lpp"] == 120.5
        assert result.loc[0, "loa"] == 125.25
        assert result.loc[0, "breadth"] == 22.0
        assert result.loc[0, "depth"] == 8.75

    def test_parse_file_reads_project_name_before_general_particulars(self, tmp_path):
        lines = valid_main_dimensions_lines()
        lines[0] = "header without project name\n"
        lines.insert(10, "{Project name : EarlyShip}\n")
        file_path = write_main_dimensions_file(tmp_path, lines)
        parser = make_parser()
        result = parser.parse_file(file_path)
        assert result.loc[0, "name"] == "EarlyShip"

    def test_parse_file_ignores_dimension_values_before_general_particulars(
        self, tmp_path
    ):
        lines = [
            "{Project name : TestShip}\n",
            rtf_value_line("Length overall", "999"),
        ]
        lines.extend(["ignored before general particulars\n"] * 29)
        lines.append(rtf_value_line("Length between perpendiculars", "120"))
        lines.append(rtf_value_line("Length overall", "125"))
        lines.append(rtf_value_line("Moulded breadth", "22"))
        lines.append(rtf_value_line("Moulded depth", "8"))
        file_path = write_main_dimensions_file(tmp_path, lines)
        parser = make_parser()
        result = parser.parse_file(file_path)
        assert result.loc[0, "loa"] == 125.0

    def test_parse_file_raises_when_required_value_is_after_frame_spacing_section(
        self, tmp_path
    ):
        lines = ["{Project name : TestShip}\n"]
        lines.extend(["ignored before general particulars\n"] * 30)
        lines.append(rtf_value_line("Length between perpendiculars", "120"))
        lines.append(rtf_value_line("Length overall", "125"))
        lines.append(rtf_value_line("Moulded breadth", "22"))
        lines.extend(["still inside section\n"] * 14)
        lines.append(rtf_value_line("Moulded depth", "8"))
        file_path = write_main_dimensions_file(tmp_path, lines)
        parser = make_parser()
        with pytest.raises(Exception) as error:
            parser.parse_file(file_path)

        assert "RTF Value Missing: Moulded depth" in str(error.value)

    def test_parse_file_raises_clear_error_when_required_value_is_missing(
        self, tmp_path
    ):
        lines = valid_main_dimensions_lines()
        lines = [line for line in lines if "Moulded breadth" not in line]
        file_path = write_main_dimensions_file(tmp_path, lines)
        parser = make_parser()
        with pytest.raises(Exception) as error:
            parser.parse_file(file_path)

        assert "RTF Value Missing: Moulded breadth" in str(error.value)

    def test_parse_file_prints_unexpected_error_for_invalid_numeric_value(
        self, tmp_path, capsys
    ):
        lines = valid_main_dimensions_lines()
        lines = [
            (
                rtf_value_line("Moulded breadth", "not numeric")
                if "Moulded breadth" in line
                else line
            )
            for line in lines
        ]
        file_path = write_main_dimensions_file(tmp_path, lines)
        parser = make_parser()
        with pytest.raises(Exception, match="RTF Value Missing"):
            parser.parse_file(file_path)

        assert "An unexpected error occurred" in capsys.readouterr().out

    def test_parse_file_prints_file_not_found_and_raises_missing_values(self, capsys):
        parser = make_parser()
        with pytest.raises(Exception, match="RTF Value Missing"):
            parser.parse_file("does-not-exist.rtf")

        assert "was not found" in capsys.readouterr().out

    def test_parse_file_prints_permission_error_and_raises_missing_values(
        self, monkeypatch, capsys
    ):
        def raise_permission_error(*args, **kwargs):
            raise PermissionError

        monkeypatch.setattr(builtins, "open", raise_permission_error)
        parser = make_parser()
        with pytest.raises(Exception, match="RTF Value Missing"):
            parser.parse_file("blocked.rtf")

        assert "Permission denied" in capsys.readouterr().out

    def test_parse_file_prints_unicode_error_and_raises_missing_values(
        self, monkeypatch, capsys
    ):
        def raise_unicode_error(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        monkeypatch.setattr(builtins, "open", raise_unicode_error)
        parser = make_parser()
        with pytest.raises(Exception, match="RTF Value Missing"):
            parser.parse_file("bad-encoding.rtf")

        assert "Could not decode" in capsys.readouterr().out

    def test_parse_file_prints_unexpected_error_and_raises_missing_values(
        self, monkeypatch, capsys
    ):
        def raise_unexpected_error(*args, **kwargs):
            raise RuntimeError("error")

        monkeypatch.setattr(builtins, "open", raise_unexpected_error)
        parser = make_parser()
        with pytest.raises(Exception, match="RTF Value Missing"):
            parser.parse_file("unexpected.rtf")

        assert "An unexpected error occurred: error" in capsys.readouterr().out
