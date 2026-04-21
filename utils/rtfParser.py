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
            "Length Between Perpendiculars",
            "Waterline Length",
            "Length Overall",
            "Moulded Breadth",
            "Design Draft",
            "Moulded Depth",
            "Appendage coefficient",
            "Mean shell plate thickness",
            "Keel plate thickness",
            "Number of persons for whome lifeboats are provided (N1)",
            "Subdivision Length",
            "Light service draft",
            "Subdivision draft",
            "Number of persons for whome lifeboats are provided (N1)",
            "Number of persons for whome NO lifeboats are provided (N2)",
        ]
        self.output_df = pd.DataFrame(columns=self.cols)

    def parse_file(self, file_path) -> pd.DataFrame:
        try:
            with open(file_path, "r", encoding="rtf") as file:
                for idx, line in enumerate(file):
                    if idx < self.GENERAL_PARTICULARS_START:
                        continue
                    elif idx > self.FRAME_SPACING_DEFS_START:
                        break
                    else:
                        print(f"The line being parsed is: {line}")

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
