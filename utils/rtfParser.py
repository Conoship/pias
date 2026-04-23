import pandas as pd


class MainDimensionsParser(object):
    GENERAL_PARTICULARS_START = 31
    FRAME_SPACING_DEFS_START = 47

    def __init__(self):
        self.cols = [
            "Length between perpendiculars",
            "Moulded breadth",
            "Moulded depth",
        ]
        self.output_df = pd.DataFrame(columns=self.cols)

    def find_all_occurrences(self, text: str, char: str):
        """
        Returns a list of all indices where `char` occurs in `text`.
        Handles edge cases like empty strings, multi-character input, etc.
        """
        # Input validation
        if not isinstance(text, str) or not isinstance(char, str):
            raise TypeError("Both text and char must be strings.")
        if len(char) != 1:
            raise ValueError("The 'char' argument must be a single character.")

        # Find all occurrences
        return [i for i, c in enumerate(text) if c == char]

    def parse_file(self, file_path) -> pd.DataFrame:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                column_searching = 0
                for idx, line in enumerate(file):
                    if idx < self.GENERAL_PARTICULARS_START:
                        continue
                    if idx > self.FRAME_SPACING_DEFS_START:
                        break
                    if self.cols[column_searching] in line:
                        # Get all occureneces of  the character '{', then remove the last indices because they were used in "{m}".
                        opening_curly_brace_indices = self.find_all_occurrences(
                            line, "{"
                        )
                        opening_curly_brace_indices.pop()

                        # Get all occureneces of  the character '}', then remove the last indices because they were used in "{m}".
                        closing_curly_brace_indices = self.find_all_occurrences(
                            line, "}"
                        )
                        closing_curly_brace_indices.pop()

                        # The last occurence of the character '{' is right before the value of the feature we are searching for.
                        # To get the full value we will search from one position after the start of '{' untill we encounter '}'.
                        start_index, end_index = (
                            opening_curly_brace_indices[-1],
                            closing_curly_brace_indices[-1],
                        )
                        feature_value = line[start_index + 1 : end_index]
                        self.output_df.loc[0, self.cols[column_searching]] = (
                            feature_value
                        )

                        # Check if we are done parsing the data we need.
                        if self.cols[column_searching] == self.cols[len(self.cols) - 1]:
                            break

                        # Increment counter to go to the next column.
                        column_searching += 1

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")

        except PermissionError:
            print(f"Error: Permission denied to read '{file_path}'.")

        except UnicodeDecodeError:
            print(f"Error: Could not decode '{file_path}' with UTF-8 encoding.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        return self.output_df


def main():
    file_path = "C:/Users/student01/Documents/Stephanie/Clean/Concept Design/A3072/v00 - initial run new hull/main.rtf"
    parser = MainDimensionsParser()
    data = parser.parse_file(file_path)
    print(data)


if __name__ == "__main__":
    main()
