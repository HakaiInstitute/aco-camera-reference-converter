import pytest
from csrspy.enums import Reference, VerticalDatum, CoordType

from aco_camera_csv_converter.models import (
    TransformationParameters,
    CoordinateData,
    TransformationInput,
)


class TestTransformationParameters:
    """Test TransformationParameters data model."""

    def test_to_csrspy_kwargs(self):
        """Test conversion to CSRSTransformer kwargs."""
        params = TransformationParameters(
            s_ref_frame=Reference.WGS84,
            s_coords=CoordType.GEOG,
            s_vd=VerticalDatum.WGS84,
            s_epoch=2020.0,
            t_ref_frame=Reference.NAD83CSRS,
            t_coords=CoordType.UTM10,
            t_vd=VerticalDatum.CGG2013A,
            t_epoch=2002.0,
        )

        kwargs = params.to_csrspy_kwargs()

        assert kwargs == {
            "s_ref_frame": Reference.WGS84,
            "s_coords": CoordType.GEOG,
            "s_vd": VerticalDatum.WGS84,
            "s_epoch": 2020.0,
            "t_ref_frame": Reference.NAD83CSRS,
            "t_coords": CoordType.UTM10,
            "t_vd": VerticalDatum.CGG2013A,
            "t_epoch": 2002.0,
        }


class TestCoordinateData:
    """Test CoordinateData model."""

    def test_valid_coordinate_data(self):
        """Test valid coordinate data creation."""
        coords = [(123.45, 67.89, 100.0), (124.45, 68.89, 101.0)]
        coord_data = CoordinateData(coord_type="dd", coordinates=coords)

        assert coord_data.coord_type == "dd"
        assert coord_data.coordinates == coords

    def test_empty_coordinates_raises_error(self):
        """Test that empty coordinates list raises ValueError."""
        with pytest.raises(ValueError, match="Coordinates list cannot be empty"):
            CoordinateData(coord_type="dd", coordinates=[])

    def test_invalid_coordinate_tuple_raises_error(self):
        """Test that invalid coordinate tuples raise ValueError."""
        with pytest.raises(ValueError, match="Coordinate 0 must have exactly 3 values"):
            CoordinateData(
                coord_type="dd", coordinates=[(123.45, 67.89)]
            )  # Missing altitude

        with pytest.raises(ValueError, match="Coordinate 1 must have exactly 3 values"):
            CoordinateData(
                coord_type="dd",
                coordinates=[
                    (123.45, 67.89, 100.0),
                    (124.45, 68.89, 101.0, 102.0),  # Too many values
                ],
            )


class TestTransformationInput:
    """Test TransformationInput model."""

    @pytest.fixture
    def sample_transformation_params(self):
        """Sample transformation parameters."""
        return TransformationParameters(
            s_ref_frame=Reference.WGS84,
            s_coords=CoordType.GEOG,
            s_vd=VerticalDatum.WGS84,
            s_epoch=2020.0,
            t_ref_frame=Reference.NAD83CSRS,
            t_coords=CoordType.UTM10,
            t_vd=VerticalDatum.CGG2013A,
            t_epoch=2002.0,
        )

    @pytest.fixture
    def sample_coordinate_data(self):
        """Sample coordinate data."""
        return CoordinateData(
            coord_type="dd",
            coordinates=[(123.45, 67.89, 100.0), (124.45, 68.89, 101.0)],
        )

    def test_get_summary(self, sample_transformation_params, sample_coordinate_data):
        """Test transformation input summary generation."""
        import polars as pl

        df = pl.DataFrame(
            {
                "Timestamp": ["2023-01-01", "2023-01-02"],
                "Filename": ["img1.iiq", "img2.iiq"],
                "Origin (Latitude[deg]": [67.89, 68.89],
                "Longitude[deg]": [123.45, 124.45],
                "Altitude[m])": [100.0, 101.0],
            }
        )

        transformation_input = TransformationInput(
            transformation_params=sample_transformation_params,
            coordinate_data=sample_coordinate_data,
            original_df=df,
        )

        summary = transformation_input.get_summary()

        expected_summary = {
            "source_reference_frame": "WGS84",
            "source_coord_type": "GEOG",
            "source_vertical_datum": "WGS84",
            "source_epoch": 2020.0,
            "target_reference_frame": "NAD83CSRS",
            "target_coord_type": "UTM10",
            "target_vertical_datum": "CGG2013A",
            "target_epoch": 2002.0,
            "coordinate_type": "dd",
            "num_coordinates": 2,
            "first_coordinate": (123.45, 67.89, 100.0),
            "last_coordinate": (124.45, 68.89, 101.0),
        }

        assert summary == expected_summary
