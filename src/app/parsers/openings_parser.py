import psycopg
from pathlib import Path
import pdfplumber

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
        stem = file_path.name

        # strip optional "_openings" suffix before extension
        if stem.lower().endswith("_openings"):
            stem = stem[: -len("_openings")]

        parts = stem.split("_")

        ship = parts[0] if len(parts) > 0 else "unknownship"
        design = parts[1] if len(parts) > 1 else "unknowndesign"
        version = parts[2] if len(parts) > 2 else "unknownversion"
        subversion = "_".join(parts[3:]) if len(parts) > 3 else ""

        return ship.strip(), design.strip(), version.strip(), subversion.strip()


    def _parse_float(self, text: str | None) -> float | None:
        if text is None:
            return None
        try:
            return float(text.strip())
        except ValueError:
            return None

    
    
    def parse_openings(self, pdf_path: str | Path) -> pd.DataFrame:
        pdf_path = Path(pdf_path)

        ship, design, version, subversion = self._parse_filename(pdf_path)

        rows = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []

                for table in tables:
                    for row in table:
                        if not row or all(cell is None for cell in row):
                            continue

                        # skip header row
                        if row[0] and "Description" in row[0]:
                            continue

                        if len(row) < 6:
                            continue

                        rows.append({
                            "ship": ship,
                            "design": design,
                            "version": version,
                            "subversion": subversion,
                            "description": (row[0] or "").strip(),
                            "length": self._parse_float(row[1]),
                            "breadth": self._parse_float(row[2]),
                            "height": self._parse_float(row[3]),
                            "opening_type": (row[4] or "").strip(),
                            "connected": (row[5] or "").strip(),
                        })

        self._df = pd.DataFrame(rows, columns=self._cols)
        return self._df



