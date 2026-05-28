# Import standard library packages.
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Import third party packages.
import pandas as pd


class LayoutsParser(object):
    def __init__(self) -> None:
        """
        Parser class for the Layout XML file based on `parseLayout.py`.
        """
        self._cols = [
            "source_file",
            "ship",
            "design_name",
            "version",
            "subversion",
            "ship_run",
            "record_type",
            "design_content_id_number",
            "content_category_name",
            "shape_guid",
            "side",
            "subcompartment_shape_type",
            "span_b",
            "span_h",
            "aftfwd_and_num",
            "L",
            "B",
            "H",
            "xml_compartment_id",
            "xml_compartment_guid",
            "compartment_name",
            "selected_for_output",
            "subcompartment_guid",
            "sign",
            "permeability_for_damage_stability",
            "is_pipe",
            "opening_description",
            "opening_type",
        ]
        self._df = pd.DataFrame(columns=self._cols)

    def _parse_filename(self, file_path: Path) -> tuple[str, str, str, str, str]:
        """
        Extracts ship, design, version, subversion and ship run from the file name.

        Args:
            file_path (Path):
                The path to the `.xml` file to parse.

        Returns:
            tuple[str, str, str, str, str]:
                The ship, design name, version, subversion and ship run.
        """
        stem = file_path.name
        if stem.endswith(".fromLayout.xml"):
            stem = stem[: -len(".fromLayout.xml")]
        else:
            stem = file_path.stem

        parts = stem.split("_")

        ship = parts[0] if len(parts) > 0 else "unknownship"
        design_name = parts[1] if len(parts) > 1 else "unknowndesign"
        version = parts[2] if len(parts) > 2 else "unknownversion"
        subversion = parts[3] if len(parts) > 3 else ""
        ship_run = "_".join(parts[4:]) if len(parts) > 4 else ""

        return (
            ship.strip(),
            design_name.strip(),
            version.strip(),
            subversion.strip(),
            ship_run.strip(),
        )

    def _parse_float(self, text: str | None) -> float | None:
        """
        Converts XML text to a float value.

        Args:
            text (str | None):
                The XML text value to convert.

        Returns:
            float | None:
                The parsed float value, or None when the value cannot be parsed.
        """
        if text is None:
            return None

        value = text.strip()
        if value.upper() in ("INF", "-INF"):
            return None

        try:
            return float(value)
        except ValueError:
            return None

    def _parse_int(self, text: str | None) -> int | None:
        """
        Converts XML text to an integer value.

        Args:
            text (str | None):
                The XML text value to convert.

        Returns:
            int | None:
                The parsed integer value, or None when the value cannot be parsed.
        """
        if text is None:
            return None

        try:
            return int(text.strip())
        except ValueError:
            return None

    def _load_xml(self, file_path: Path) -> ET.Element:
        """
        Loads the XML file and returns its root element.

        Args:
            file_path (Path):
                The path to the `.xml` file to parse.

        Returns:
            ET.Element:
                The root element of the XML file.
        """
        tree = ET.parse(file_path)
        return tree.getroot()

    def _base_row(self, file_path: Path) -> dict:
        """
        Builds the base row values shared by all parsed records.

        Args:
            file_path (Path):
                The path to the `.xml` file to parse.

        Returns:
            dict:
                The shared source and ship version metadata.
        """
        ship, design_name, version, subversion, ship_run = self._parse_filename(
            file_path
        )

        return {
            "source_file": str(file_path),
            "ship": ship,
            "design_name": design_name,
            "version": version,
            "subversion": subversion,
            "ship_run": ship_run,
        }

    def _get_reference_coordinates(
        self, element: ET.Element
    ) -> tuple[float | None, float | None, float | None]:
        """
        Extracts L, B and H coordinates from a reference vector element.

        Args:
            element (ET.Element):
                The XML element that may contain a Reference_vector child.

        Returns:
            tuple[float | None, float | None, float | None]:
                The parsed L, B and H coordinates.
        """
        ref = element.find("Reference_vector")
        if ref is None:
            return None, None, None

        l = self._parse_float(ref.findtext("L/Reference_value/Distance"))
        b = self._parse_float(ref.findtext("B/Reference_value/Distance"))
        h = self._parse_float(ref.findtext("H/Reference_value/Distance"))

        return l, b, h

    def _parse_content_categories(self, root: ET.Element, base_row: dict) -> list[dict]:
        """
        Parses content category records from the XML file.

        Args:
            root (ET.Element):
                The root element of the XML file.

            base_row (dict):
                The shared source and ship version metadata.

        Returns:
            list[dict]:
                The parsed content category rows.
        """
        rows = []

        for content_category in root.findall(".//Content_categories/Content_category"):
            design_content_id = self._parse_int(
                content_category.findtext("Design_content_IDnumber")
            )
            name = content_category.findtext("Name")

            if design_content_id is None or not name:
                continue

            row = {
                **base_row,
                "record_type": "content_category",
                "design_content_id_number": design_content_id,
                "content_category_name": name,
            }
            rows.append(row)

        return rows

    def _parse_coordinates(
        self, root: ET.Element, base_row: dict
    ) -> tuple[list[dict], dict[str, tuple[float | None, float | None]]]:
        """
        Parses subcompartment shapes and frustum points from the XML file.

        Args:
            root (ET.Element):
                The root element of the XML file.

            base_row (dict):
                The shared source and ship version metadata.

        Returns:
            tuple[list[dict], dict[str, tuple[float | None, float | None]]]:
                The parsed coordinate rows and shape breadth/height spans.
        """
        rows = []
        shape_guid_spans = {}

        for shape in root.findall(".//Subcompartment_shapes/Subcompartment_shape"):
            shape_guid = shape.findtext("Subcompartment_shape_GUID")
            if not shape_guid:
                continue

            side = shape.findtext("Side")
            shape_type = shape.findtext("Subcompartment_shape_type")
            frustum_rows = []
            bs = []
            hs = []

            if shape_type == "shapetype_frustum":
                for frustum_point in shape.findall(".//Frustum_points/Frustum_point"):
                    l, b, h = self._get_reference_coordinates(frustum_point)

                    if b is not None:
                        bs.append(b)
                    if h is not None:
                        hs.append(h)

                    frustum_rows.append(
                        {
                            **base_row,
                            "record_type": "frustum_point",
                            "shape_guid": shape_guid,
                            "side": side,
                            "subcompartment_shape_type": shape_type,
                            "aftfwd_and_num": frustum_point.findtext(
                                "AftFwd_and_number"
                            ),
                            "L": l,
                            "B": b,
                            "H": h,
                        }
                    )

            span_b = max(bs) - min(bs) if len(bs) >= 2 else None
            span_h = max(hs) - min(hs) if len(hs) >= 2 else None
            shape_guid_spans[shape_guid] = (span_b, span_h)

            rows.append(
                {
                    **base_row,
                    "record_type": "subcompartment_shape",
                    "shape_guid": shape_guid,
                    "side": side,
                    "subcompartment_shape_type": shape_type,
                    "span_b": span_b,
                    "span_h": span_h,
                }
            )
            rows.extend(frustum_rows)

        return rows, shape_guid_spans

    def _parse_compartments(
        self,
        root: ET.Element,
        base_row: dict,
        shape_guid_spans: dict[str, tuple[float | None, float | None]],
    ) -> list[dict]:
        """
        Parses compartments, subcompartments and openings from the XML file.

        Args:
            root (ET.Element):
                The root element of the XML file.

            base_row (dict):
                The shared source and ship version metadata.

            shape_guid_spans (dict[str, tuple[float | None, float | None]]):
                The breadth and height spans for each shape GUID.

        Returns:
            list[dict]:
                The parsed compartment, subcompartment and opening rows.
        """
        rows = []

        for compartment in root.findall(".//Compartment"):
            selected = (
                compartment.findtext("Selected_for_output_and_calculations") or ""
            ).strip().lower() == "true"
            if not selected:
                continue

            xml_compartment_id = self._parse_int(compartment.findtext("Compartment_ID"))
            xml_compartment_guid = compartment.findtext("Compartment_GUID")
            compartment_name = compartment.findtext("Name") or ""
            design_content_id = self._parse_int(
                compartment.findtext("Design_content_IDnumber")
            )

            compartment_row = {
                **base_row,
                "record_type": "compartment",
                "xml_compartment_id": xml_compartment_id,
                "xml_compartment_guid": xml_compartment_guid,
                "compartment_name": compartment_name,
                "selected_for_output": selected,
                "design_content_id_number": design_content_id,
            }
            rows.append(compartment_row)

            name_lower = compartment_name.lower()
            contains_pipe = "pipe" in name_lower
            contains_pipeduct = "pipeduct" in name_lower or "pipe duct" in name_lower

            for subcompartment in compartment.findall(
                ".//Subcompartments/Subcompartment"
            ):
                shape_guid = subcompartment.findtext("Shape_GUID")
                if shape_guid is None:
                    span_b, span_h = None, None
                else:
                    span_b, span_h = shape_guid_spans.get(shape_guid, (None, None))
                small_b = span_b is not None and span_b < 0.3
                small_h = span_h is not None and span_h < 0.3
                is_pipe = bool(
                    contains_pipe and not contains_pipeduct and (small_b or small_h)
                )

                rows.append(
                    {
                        **compartment_row,
                        "record_type": "subcompartment",
                        "shape_guid": shape_guid,
                        "subcompartment_guid": subcompartment.findtext(
                            "Subcompartment_GUID"
                        ),
                        "sign": self._parse_int(subcompartment.findtext("Sign")),
                        "permeability_for_damage_stability": self._parse_float(
                            subcompartment.findtext("Permeability_for_damage_stability")
                        ),
                        "span_b": span_b,
                        "span_h": span_h,
                        "is_pipe": is_pipe,
                    }
                )

            for point in compartment.findall(".//Special_points/Point"):
                l, b, h = self._get_reference_coordinates(point)

                rows.append(
                    {
                        **compartment_row,
                        "record_type": "opening",
                        "opening_description": point.findtext("Name") or "",
                        "opening_type": point.findtext("Type_of_point") or "",
                        "L": l,
                        "B": b,
                        "H": h,
                    }
                )

        return rows

    def _is_missing(self, value: Any) -> bool:
        """
        Checks if a parsed DataFrame value should be treated as missing.

        Args:
            value (object):
                The value to check.

        Returns:
            bool:
                `True` if the value is missing, `False` otherwise.
        """
        return bool(pd.isna(value) or (isinstance(value, str) and value.strip() == ""))

    def _validate_df(self) -> None:
        """
        Method to validate the filled DataFrame before returning it in `parse_file`.

        Raises:
            Exception:
                In case the DataFrame is empty, has missing columns, contains an
                unknown record type, or misses required values for a record type.
        """
        if self._df.empty:
            raise Exception("Parser could not extract any layout records.")

        missing_columns = [col for col in self._cols if col not in self._df.columns]
        if missing_columns:
            missing_column_names = ", ".join(missing_columns)
            raise Exception(
                "Parser output is missing expected columns: " f"{missing_column_names}."
            )

        missing_values = []

        for idx, row in self._df.iterrows():
            record_type_value = row["record_type"]
            if self._is_missing(record_type_value):
                missing_values.append(f"row {idx}: record_type")
                continue

        if missing_values:
            missing_value_names = ", ".join(missing_values)
            raise Exception(
                "Parser could not fill all required layout values, "
                f"possibly due to missing values for: {missing_value_names}."
            )

    def parse_file(self, file_path: str) -> pd.DataFrame:
        """
        Method to parse the XML file.

        Args:
            file_path (str):
                The path to the `.xml` file to parse.

        Returns:
            pd.DataFrame:
                The resulting pandas DataFrame that contains all parsed layout data.
        """
        xml_path = Path(file_path)
        rows = []

        try:
            xml_root = self._load_xml(xml_path)
            base_row = self._base_row(xml_path)

            rows.extend(self._parse_content_categories(xml_root, base_row))
            coordinate_rows, shape_guid_spans = self._parse_coordinates(
                xml_root, base_row
            )
            rows.extend(coordinate_rows)
            rows.extend(self._parse_compartments(xml_root, base_row, shape_guid_spans))

            self._df = pd.DataFrame(rows, columns=self._cols)

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")

        except PermissionError:
            print(f"Error: Permission denied to read '{file_path}'.")

        except ET.ParseError as e:
            print(f"Error: Could not parse '{file_path}' as XML: {e}")

        except Exception as e:
            print(f"There was an error parsing the file: {e}")

        self._validate_df()

        return self._df
