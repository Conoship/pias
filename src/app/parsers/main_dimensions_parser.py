# Import standard library packages.
import re

# Import third party packages.
import pandas as pd


class MainDimensionsParser(object):
    # The number of the line where the General Particulars Section starts.
    _GENERAL_PARTICULARS_START = 31

    # The number of the line where the Frame Spacing Definitions start.
    _FRAME_SPACING_DEFS_START = 47

    # List of all columns that we accept being missing in the RTF file.
    # TODO: Implement this.
    _ACCEPT_MISSING_COLS = ()

    def __init__(self) -> None:
        """
        Parser class for the Main Dimensions RTF file.
        """
        self._cols = [
            "Length between perpendiculars",
            "Length overall",
            "Moulded breadth",
            "Moulded depth",
        ]
        self._df = pd.DataFrame(columns=self._cols)

    def _extract_field_value(self, line: str, feature_name: str) -> str | None:
        """
        Extracts the value associated with a field name in an RTF line.

        This is done by:
        - Locating the field name in the line.
        - Capturing the second {...} group that follows it.

        This avoids interference from other RTF braces.

        Args:
            line (str):
                The line being parsed in the RTF file.

            feature_name (str):
                The name of the feature that we are searching for its value.
        """
        if feature_name not in line:
            return None

        # Isolate the relevant section.
        start = line.find(feature_name)
        if start == -1:
            return None

        # Find all {} occurences in order.
        substring = line[start:]
        matches = list(re.finditer(r"\{(.*?)\}", substring))

        # Extract the value from the correct one.
        if len(matches) >= 3:
            return matches[1].group(1).strip()

        return None

    def _parse_float(self, value: str) -> float:
        """
        Converts a parsed RTF field value to a float.

        Args:
            value (str):
                The parsed RTF field value.

        Raises:
            ValueError:
                If the parsed value cannot be converted to a float.

        Returns:
            float:
                The parsed float value.
        """
        return float(value.replace(",", "."))

    def _validate_df(self) -> None:
        """
        Method to validate the filled DataFrame before returning it in `parse_file` for missing values.

        Raises:
            Exception:
                In case a column, that is not in `_ACCEPT_MISSING_COLS` does not have a value.
        """
        missing_cols = []

        for col in self._cols:
            if col in self._ACCEPT_MISSING_COLS:
                continue

            if col not in self._df.columns or self._df.empty:
                missing_cols.append(col)
                continue

            values = self._df[col]
            has_value = values.apply(
                lambda value: not (
                    pd.isna(value)
                    or (isinstance(value, str) and value.strip() == "")
                )
            ).any()

            if not has_value:
                missing_cols.append(col)

        if missing_cols:
            missing_col_names = ", ".join(missing_cols)
            raise Exception(
                "Parser could not fill all required columns of the DataFrame, "
                f"possibly due to missing values for: {missing_col_names}."
            )

    def parse_file(self, file_path: str) -> pd.DataFrame:
        """
        Method to parse the RTF file.

        Args:
            file_path (str):
                The path to the `.rtf` file to parse

        Raises:
            Exception:
                In case `self._df` fails validation.
        Returns:
            pd.DataFrame:
                The resulting pandas DataFrame
                that contains the Length Between Perpendiculars, Moulded breadth and
                Moulded Deapth.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                column_searching = 0
                for idx, line in enumerate(file):
                    if idx < self._GENERAL_PARTICULARS_START:
                        continue
                    if idx > self._FRAME_SPACING_DEFS_START:
                        break

                    current_col = self._cols[column_searching]

                    # Extract value safely using field-aware regex.
                    value = self._extract_field_value(line, current_col)

                    if value is not None:
                        self._df.loc[0, current_col] = self._parse_float(value)

                        # Move to next column only when value is found.
                        if column_searching < len(self._cols) - 1:
                            column_searching += 1
                        else:
                            break

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")

        except PermissionError:
            print(f"Error: Permission denied to read '{file_path}'.")

        except UnicodeDecodeError:
            print(f"Error: Could not decode '{file_path}' with UTF-8 encoding.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        try:
            # Validate the DataFrame.
            self._validate_df()

            # Before returning the DataFrame, rename the columns to match the ones in the database.
            renamed_cols = ["lpp", "loa", "breadth", "depth"]
            self._df.rename(
                columns={old: new for old, new in zip(self._cols, renamed_cols)},
                inplace=True,
            )
            return self._df

        except Exception as e:
            raise e
