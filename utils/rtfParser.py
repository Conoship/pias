import re
import pandas as pd


class MainDimensionsParser(object):
    _GENERAL_PARTICULARS_START = 31
    _FRAME_SPACING_DEFS_START = 47

    def __init__(self) -> None:
        self.cols = [
            "Length between perpendiculars",
            "Moulded breadth",
            "Moulded depth",
        ]
        self.output_df = pd.DataFrame(columns=self.cols)

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
            return matches[2].group(1).strip()

        return None

    def parse_file(self, file_path: str) -> pd.DataFrame:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                column_searching = 0
                for idx, line in enumerate(file):
                    if idx < self._GENERAL_PARTICULARS_START:
                        continue
                    if idx > self._FRAME_SPACING_DEFS_START:
                        break

                    current_col = self.cols[column_searching]

                    # Extract value safely using field-aware regex.
                    value = self._extract_field_value(line, current_col)

                    if value is not None:
                        self.output_df.loc[0, current_col] = value

                        # Move to next column only when value is found.
                        if column_searching < len(self.cols) - 1:
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

        return self.output_df
