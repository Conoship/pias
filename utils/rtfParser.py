import pandas as pd

class MainDimensionsParser(object):
    GENERAL_PARTICULARS_START = 31
    FRAME_SPACING_DEFS_START = 50
    LINE_LEN_AFTER_VALUE = 8
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
                        print (f"searching {self.cols[column_searching]} in {[line]}")
                        if self.cols[column_searching] in line:
                            print(f"{line} contains value for {self.cols[column_searching]}")
                            print(f"{self.cols[column_searching]}: {line[len(line)-8:len(line)]}")
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


class OutputParser(object):
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
