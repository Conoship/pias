import pandas as pd

class MainDimensionsParser(object):
    GENERAL_PARTICULARS_START = 31
    FRAME_SPACING_DEFS_START = 50
    # Subdivision Length
    # Light Service draft
    # Subdivision draft
    # All General particulars and main dimensions. 
    def __init__(self):
        self.cols = [
            "Length between perpendiculars",
            "Waterline length",
            "Length overall",
            "Moulded breadth",
            "Design draft",
            "Moulded depth",
            "Appendage coefficient",
            "Mean shell plate thickness",
            "Keel plate thickness",
            "Subdivision length",
            "Light service draft",
            "Subdivision draft",
        ]
        self.output_df = pd.DataFrame(columns=self.cols)

    def find_all_occurrences(self,text: str, char: str):
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
                    elif idx > self.FRAME_SPACING_DEFS_START:
                        break
                    else:
                        if self.cols[column_searching] in line:
                            # Get all occureneces of  the character '{' and remove the last one, since it is used at "{m}".
                            opening_curly_brace_indices = self.find_all_occurrences(line, '{')
                            opening_curly_brace_indices.pop()

                            # Get all occureneces of  the character '}' and remove the last one, since it is used at "{m}".
                            closing_curly_brace_indices = self.find_all_occurrences(line, '}')
                            closing_curly_brace_indices.pop()

                            # The last occurence of the character '{' is right before the value of the feature we are searching for.
                            # To get the full value we will search from one position after the start of '{' untill we encounter '}'.
                            start_index, end_index = opening_curly_brace_indices[-1], closing_curly_brace_indices[-1]  
                            feature_value = line[start_index + 1 : end_index]

                            self.output_df[self.cols[column_searching]] = feature_value
                            column_searching += 1

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")

        except PermissionError:
            print(f"Error: Permission denied to read '{file_path}'.")

        except UnicodeDecodeError:
            print(f"Error: Could not decode '{file_path}' with UTF-8 encoding.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        print(self.output_df)
        return self.output_df



class OpeningsParser(object):
    def __init__(self):
        self.output_df = pd.DataFrame()

    def parse_file(self, file_path):
        try:
            with open(file_path, "r", encoding="rtf") as file:
                pass

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")

        except PermissionError:
            print(f"Error: Permission denied to read '{file_path}'.")

        except UnicodeDecodeError:
            print(f"Error: Could not decode '{file_path}' with UTF-8 encoding.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")



def main():
    file_path = "C:/Users/student01/Documents/Stephanie/Clean/Concept Design/A3072/v00 - initial run new hull/main.rtf"
    parser = MainDimensionsParser()
    parser.parse_file(file_path)


if __name__ == "__main__":
    main()
