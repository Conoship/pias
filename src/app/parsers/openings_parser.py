import psycopg
from pathlib import Path
import pdfplumber
import pandas as pd
import re

import os
from dotenv import load_dotenv

load_dotenv()


class OpeningsParser(object):
    def __init__(self) -> None:
        """
        Parser class for the Openings XML file based on `parseOpenings.py`.
        """
        self._cols = [
            "ship_version_id",
            "compartment_id",
            "description",
            "length",
            "breadth",
            "height",
            "opening_type",
            "connected",
        ]
        self._df = pd.DataFrame(columns=self._cols)

    def _parse_filename(self, file_path: Path) -> tuple[str, str, str, str, str]:
        stem = file_path.stem

        # strip optional "_openings" suffix before extension
        if stem.lower().endswith("_openings"):
            stem = stem[: -len("_openings")]

        parts = stem.split("_")

        ship = parts[0] if len(parts) > 0 else "unknownship"
        design = parts[1] if len(parts) > 1 else "unknowndesign"
        version = parts[2] if len(parts) > 2 else "unknownversion"

        return ship.strip(), design.strip(), version.strip()

    def _parse_float(self, text: str | None) -> float | None:
        if text is None:
            return None
        try:
            return float(text.strip())
        except ValueError:
            return None

    def parse_openings(self, pdf_path: str | Path) -> pd.DataFrame:
        pdf_path = Path(pdf_path)

        ship, design, version = self._parse_filename(pdf_path)

        rows = []
        found_table = False

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""

                for line in text.split("\n"):
                    line = line.strip()

                    if not line:
                        continue

                    lower = line.lower()

                    # Skip row if it is the title:
                    if (
                        "description" in lower
                        and "length" in lower
                        and "breadth" in lower
                        and "height" in lower
                        and "type of point" in lower
                        and "connected with compartment" in lower
                    ):
                        found_table = True
                        continue

                    if not found_table:
                        continue

                    if "list of special points" in lower:
                        continue

                    # Split the row into columns:
                    match = re.match(
                        r"^(.*)\s+"
                        r"(-?\d+(?:[.,]\d+)?)\s+"
                        r"(-?\d+(?:[.,]\d+)?)\s+"
                        r"(-?\d+(?:[.,]\d+)?)\s+"
                        r"(.+?)\s+"
                        r"([A-Z][A-Za-z0-9\s\-\/]*|-)$",
                        line,
                    )

                    if not match:
                        print("Could not parse:", repr(line))
                        continue

                    rows.append(
                        {
                            "ship": ship,
                            "design": design,
                            "version": version,
                            "description": match.group(1).strip(),
                            "length": self._parse_float(match.group(2)),
                            "breadth": self._parse_float(match.group(3)),
                            "height": self._parse_float(match.group(4)),
                            "opening_type": match.group(5).strip(),
                            "connected": match.group(6).strip(),
                        }
                    )

        self._df = pd.DataFrame(rows)
        return self._df


# Testing the parser:
# parser = OpeningsParser()
# path = "c:/Users/student01/Documents/Stephanie/Clean/A2994_Concept_v1_ps_Openings.pdf"
# df = parser.parse_openings(path)
# print(df)
