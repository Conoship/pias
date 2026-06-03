# Import standard library packages.
import builtins

# Import third party packages.
import pandas as pd
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

# Import local packages.
from src.app.parsers.layouts_parser import LayoutsParser


def make_parser() -> LayoutsParser:
    return LayoutsParser()

def write_layouts_file(tmp_path, text: str) -> str:
    file_path = tmp_path / "layout.xml"
    file_path.write_text(text, encoding="utf-8")
    return file_path

class TestInit:
    def test_parser_starts_with_expected_columns(self):
        parser = make_parser()
        assert list(parser._df.columns) == [
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

    def test_parser_starts_with_empty_dataframe(self):
        parser = make_parser()
        assert parser._df.empty

class TestParseFilename:
    def test_parse_filename_correct_ship_attributes(self):
        parser = make_parser()
        result = parser._parse_filename("A11111_1_v2_S_01.fromLayout.xml")
        assert result == (
            "A11111",
            "1",
            "v2",
            "S",
            "01",
        )

    def test_parse_filename_missing_some_ship_attributes(self):
        parser = make_parser()
        result = parser._parse_filename("A11111.fromLayout.xml")
        assert result == (
            "A11111",
            "unknowndesign",
            "unknownversion",
            "",
            "",
        )
    
    def test_parse_filename_multiple_underscores_in_last_attributr(self):
        parser = make_parser()
        result = parser._parse_filename("A11011_3_v6_PS_Run_1.fromLayout.xml")
        assert result == (
            "A11011",
            "3",
            "v6",
            "PS",
            "Run_1",
        )

class TestParseFloat:
    def test_parse_float_returns_none_for_infinity(self):
        parser = make_parser()
        result = parser._parse_float("INF")
        assert result is None

    def test_parse_float_returns_none_for_empty_text(self):
        parser = make_parser()
        result = parser._parse_float(None)
        assert result is None

    def test_parse_float_for_valid_float(self):
        parser = make_parser()
        result = parser._parse_float("0.0006")
        assert result == 0.0006

    def test_parse_float_returns_none_for_non_numeric_text(self):
        parser = make_parser()
        result = parser._parse_float("text instead of number")
        assert result is None

class TestParseInt:
    def test_parse_int_returns_none_for_empty_text(self):
        parser = make_parser()
        result = parser._parse_int(None)
        assert result is None

    def test_parse_int_returns_none_for_non_numeric_text(self):
        parser = make_parser()
        result = parser._parse_int("text instead of number")
        assert result is None
    
    def test_parse_int_for_valid_int(self):
        parser = make_parser()
        result = parser._parse_int("123456 ")
        assert result == 123456

class TestLoadXml:
    def test_load_xml_returns_valid_root_element(self, tmp_path):
        file_path = write_layouts_file(tmp_path, "<Layout></Layout>")
        parser = make_parser()
        result = parser._load_xml(file_path)
        assert result.tag == "Layout"

    def test_load_xml_returns_error_for_invalid_file(self, tmp_path):
        file_path = write_layouts_file(tmp_path, "<Layout>")
        parser = make_parser()
        with pytest.raises(ET.ParseError):
            parser._load_xml(file_path)

class TestBaseRow:
    def test_base_row_returns_valid_row_values(self, tmp_path):
        parser = make_parser()
        result = parser._base_row(Path("A11111_1_v2_S_01.fromLayout.xml"))
        assert result == {
            "source_file": "A11111_1_v2_S_01.fromLayout.xml",
            "ship": "A11111",
            "design_name": "1",
            "version": "v2",
            "subversion": "S",
            "ship_run": "01",
        }

class TestGetReferenceCoordinates:
    def test_get_reference_coordinates_no_values(self):
        parser = make_parser()
        element = ET.fromstring("<Layout></Layout>")
        result = parser._get_reference_coordinates(element)
        assert result == (None, None, None)
    
    def test_get_reference_coordinates(self, tmp_path):
        parser = make_parser()
        element = ET.fromstring(""" 
                                <Layout>
                                    <Reference_vector>
                                        <L>
                                            <Reference_value>
                                                <Distance>12.3</Distance>
                                            </Reference_value>
                                        </L>
                                        <B>
                                            <Reference_value>
                                                <Distance>45.6</Distance>
                                            </Reference_value>
                                        </B>
                                        <H>
                                            <Reference_value>
                                                <Distance>78.9</Distance>
                                            </Reference_value>
                                        </H>
                                    </Reference_vector>
                                </Layout>
                                """)
        result = parser._get_reference_coordinates(element)
        assert result == (12.3, 45.6, 78.9)

class TestParseContentCategories:
    def test_parse_content_categories_valid_id_and_name(self):
        parser = make_parser()
        element = ET.fromstring("""
                                <Layout>
                                    <Content_categories>
                                        <Content_category>
                                            <Design_content_IDnumber>11</Design_content_IDnumber>
                                            <Name>Category 1</Name>
                                        </Content_category>
                                    </Content_categories>
                                </Layout>
                                """)
        base_rows = {
            "source_file": "A11111_1_v2_S_01.fromLayout.xml",
            "ship": "A11111",
            "design_name": "1",
            "version": "v2",
            "subversion": "S",
            "ship_run": "01",
        }

        result = parser._parse_content_categories(element, base_rows)
        assert result[0]["record_type"] == "content_category"
        assert result[0]["design_content_id_number"] == 11
        assert result[0]["content_category_name"] == "Category 1"

    def test_parse_content_categories_missing_id(self):
        parser = make_parser()
        element = ET.fromstring("""
                                <Layout>
                                    <Content_categories>
                                        <Content_category>
                                            <Name>Category 1</Name>
                                        </Content_category>
                                    </Content_categories>
                                </Layout>
                                """)

        result = parser._parse_content_categories(element, {})
        assert result == []

    def test_parse_content_categories_missing_name(self):
        parser = make_parser()
        element = ET.fromstring("""
                                <Layout>
                                    <Content_categories>
                                        <Content_category>
                                            <Design_content_IDnumber>11</Design_content_IDnumber>
                                        </Content_category>
                                    </Content_categories>
                                </Layout>
                                """)

        result = parser._parse_content_categories(element, {})
        assert result == []

class TestParseCoordinates:
    def test_parse_coordinates_valid_shapes_and_frustum_points(self):
        parser = make_parser()
        element = ET.fromstring("""
                                <Layout>
                                    <Subcompartment_shapes>
                                        <Subcompartment_shape>
                                            <Subcompartment_shape_GUID>shape</Subcompartment_shape_GUID>
                                            <Side>side name</Side>
                                            <Subcompartment_shape_type>shapetype_frustum</Subcompartment_shape_type>
                                            <Frustum_points>
                                                <Frustum_point>
                                                    <AftFwd_and_number>01</AftFwd_and_number>
                                                        <Reference_vector>
                                                            <L><Reference_value><Distance>12.3</Distance></Reference_value></L>
                                                            <B><Reference_value><Distance>45.6</Distance></Reference_value></B>
                                                            <H><Reference_value><Distance>78.9</Distance></Reference_value></H>
                                                        </Reference_vector>
                                                </Frustum_point>
                                
                                                <Frustum_point>
                                                    <AftFwd_and_number>02</AftFwd_and_number>
                                                        <Reference_vector>
                                                            <L><Reference_value><Distance>10.1</Distance></Reference_value></L>
                                                            <B><Reference_value><Distance>30.1</Distance></Reference_value></B>
                                                            <H><Reference_value><Distance>10.1</Distance></Reference_value></H>
                                                        </Reference_vector>
                                                </Frustum_point>
                                            </Frustum_points>
                                        </Subcompartment_shape>
                                    </Subcompartment_shapes>
                                </Layout>
                                """)
        base_rows = {
            "source_file": "A11111_1_v2_S_01.fromLayout.xml",
            "ship": "A11111",
            "design_name": "1",
            "version": "v2",
            "subversion": "S",
            "ship_run": "01",
        }
        result_row, result_shape_guid_spans = parser._parse_coordinates(element, base_rows)
        assert result_row[0]["record_type"] == "subcompartment_shape"
        assert result_row[0]["shape_guid"] == "shape"
        assert result_row[0]["side"] == "side name"
        assert result_row[0]["subcompartment_shape_type"] == "shapetype_frustum"
        assert result_row[0]["span_b"] == 15.5
        assert result_row[0]["span_h"] == 68.8

        assert result_row[1]["record_type"] == "frustum_point"
        assert result_row[1]["shape_guid"] == "shape"
        assert result_row[1]["side"] == "side name"
        assert result_row[1]["subcompartment_shape_type"] == "shapetype_frustum"
        assert result_row[1]["aftfwd_and_num"] == "01"
        assert result_row[1]["L"] == 12.3
        assert result_row[1]["B"] == 45.6
        assert result_row[1]["H"] == 78.9

        assert result_row[2]["record_type"] == "frustum_point"
        assert result_row[2]["shape_guid"] == "shape"
        assert result_row[2]["side"] == "side name"
        assert result_row[2]["subcompartment_shape_type"] == "shapetype_frustum"
        assert result_row[2]["aftfwd_and_num"] == "02"
        assert result_row[2]["L"] == 10.1
        assert result_row[2]["B"] == 30.1
        assert result_row[2]["H"] == 10.1

        assert result_shape_guid_spans == {"shape": (15.5, 68.8)}

        
    def test_parse_coordinates_no_shape_guid_provided(self):
        parser = make_parser()
        element = ET.fromstring("""
                                <Layout>
                                    <Subcompartment_shapes>
                                        <Subcompartment_shape> 
                                            <Side>side name</Side>
                                            <Subcompartment_shape_type>type</Subcompartment_shape_type>                                       
                                        </Subcompartment_shape>
                                    </Subcompartment_shapes>
                                </Layout>
                                """)
        result_row, result_shape_guid_spans = parser._parse_coordinates(element, {})
        assert result_row == []
        assert result_shape_guid_spans == {}

class TestParseCompartments:
    # to add
    parser = make_parser()

class TestIsMissing:
    # to add
    parser = make_parser()
    
class TestValidateDf:
    # to add
    parser = make_parser()

class TestParseFile:
    # to add
    parser = make_parser()