import pytest
import polars as pl
from unittest.mock import Mock, patch

from aco_camera_csv_converter.services import CoordinateProcessor, TransformationService
from aco_camera_csv_converter.models import TransformationParameters
from csrspy.enums import Reference, VerticalDatum, CoordType


class TestCoordinateProcessor:
    """Test CoordinateProcessor class."""

    def test_dms_to_decimal_north_east(self):
        """Test DMS to decimal conversion for North/East coordinates."""
        result = CoordinateProcessor.dms_to_decimal("N52° 30' 45\"")
        expected = 52 + 30 / 60 + 45 / 3600
        assert abs(result - expected) < 1e-10

    def test_dms_to_decimal_south_west(self):
        """Test DMS to decimal conversion for South/West coordinates."""
        result = CoordinateProcessor.dms_to_decimal("W123° 15' 30\"")
        expected = -(123 + 15 / 60 + 30 / 3600)
        assert abs(result - expected) < 1e-10

    def test_detect_coord_type_cartesian(self):
        """Test detection of cartesian coordinates."""
        df = pl.DataFrame(
            {"Origin (X[m]": [500000.0], "Y[m]": [6000000.0], "Z[m])": [100.0]}
        )
        result = CoordinateProcessor.detect_coord_type(df)
        assert result == "cart"

    def test_detect_coord_type_dms(self):
        """Test detection of DMS coordinates."""
        df = pl.DataFrame(
            {
                "Origin (Latitude[deg]": ["N52° 30' 45\""],
                "Longitude[deg]": ["W123° 15' 30\""],
            }
        )
        result = CoordinateProcessor.detect_coord_type(df)
        assert result == "dms"

    def test_detect_coord_type_decimal_degrees(self):
        """Test detection of decimal degree coordinates."""
        df = pl.DataFrame(
            {"Origin (Latitude[deg]": [52.5125], "Longitude[deg]": [-123.258333]}
        )
        result = CoordinateProcessor.detect_coord_type(df)
        assert result == "dd"

    def test_preprocess_dataframe_dms(self):
        """Test preprocessing of DMS coordinates."""
        df = pl.DataFrame(
            {
                "Filename": ["test.iiq"],
                "Origin (Latitude[deg]": ["N52° 30' 45\""],
                "Longitude[deg]": ["W123° 15' 30\""],
            }
        )

        result = CoordinateProcessor.preprocess_dataframe(df, "dms")

        # Check that DMS coordinates were converted to decimal
        assert isinstance(result["Origin (Latitude[deg]"][0], float)
        assert isinstance(result["Longitude[deg]"][0], float)

        # Check that filename transformations were added
        assert "RGBI_Filename" in result.columns
        assert "RGB_Filename" in result.columns
        assert result["RGBI_Filename"][0] == "test_rgbi.tif"
        assert result["RGB_Filename"][0] == "test_cal.tif"

    def test_preprocess_dataframe_decimal_degrees(self):
        """Test preprocessing of decimal degree coordinates."""
        df = pl.DataFrame(
            {
                "Filename": ["test.iiq"],
                "Origin (Latitude[deg]": [52.5125],
                "Longitude[deg]": [-123.258333],
            }
        )

        result = CoordinateProcessor.preprocess_dataframe(df, "dd")

        # Check that coordinates remain as decimal
        assert result["Origin (Latitude[deg]"][0] == 52.5125
        assert result["Longitude[deg]"][0] == -123.258333

        # Check filename transformations
        assert result["RGBI_Filename"][0] == "test_rgbi.tif"
        assert result["RGB_Filename"][0] == "test_cal.tif"

    def test_extract_coordinates_geographic(self):
        """Test extraction of geographic coordinates."""
        df = pl.DataFrame(
            {
                "Origin (Latitude[deg]": [52.5125, 53.0],
                "Longitude[deg]": [-123.258333, -124.0],
                "Altitude[m])": [100.0, 150.0],
            }
        )

        result = CoordinateProcessor.extract_coordinates(df, "dd")
        expected = [(-123.258333, 52.5125, 100.0), (-124.0, 53.0, 150.0)]

        assert result == expected

    def test_extract_coordinates_cartesian(self):
        """Test extraction of cartesian coordinates."""
        df = pl.DataFrame(
            {
                "Origin (X[m]": [500000.0, 501000.0],
                "Y[m]": [6000000.0, 6001000.0],
                "Z[m])": [100.0, 150.0],
            }
        )

        result = CoordinateProcessor.extract_coordinates(df, "cart")
        expected = [(500000.0, 6000000.0, 100.0), (501000.0, 6001000.0, 150.0)]

        assert result == expected


class TestTransformationService:
    """Test TransformationService class."""

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
    def sample_geographic_df(self):
        """Sample geographic DataFrame."""
        return pl.DataFrame(
            {
                "Timestamp": ["2023-01-01", "2023-01-02"],
                "Filename": ["img1.iiq", "img2.iiq"],
                "Origin (Latitude[deg]": [52.5125, 53.0],
                "Longitude[deg]": [-123.258333, -124.0],
                "Altitude[m])": [100.0, 150.0],
                "Roll(X)[deg]": [0.0, 1.0],
                "Pitch(Y)[deg]": [0.0, 1.0],
                "Yaw(Z)[deg]": [0.0, 1.0],
                "Omega[deg]": [0.0, 1.0],
                "Phi[deg]": [0.0, 1.0],
                "Kappa[deg]": [0.0, 1.0],
            }
        )

    def test_inspection_disabled(
        self, sample_transformation_params, sample_geographic_df
    ):
        """Test transformation service with inspection disabled."""
        service = TransformationService(enable_inspection=False)

        # Mock CSRSTransformer to avoid actual transformation
        with patch(
            "aco_camera_csv_converter.services.CSRSTransformer"
        ) as mock_transformer_class:
            mock_transformer = Mock()
            mock_transformer.t_coords = CoordType.UTM10
            mock_transformer.return_value = [
                (500000.0, 6000000.0, 100.0),
                (501000.0, 6001000.0, 150.0),
            ]
            mock_transformer_class.return_value = mock_transformer

            with patch("aco_camera_csv_converter.services.sync_missing_grid_files"):
                result = service.transform_coordinates(
                    sample_geographic_df,
                    sample_transformation_params,
                    coord_type="dd",
                    should_transform=True,
                )

        # Should have no inspection data
        assert service.inspect_transformation_input() is None
        assert isinstance(result, pl.DataFrame)

    def test_inspection_enabled(
        self, sample_transformation_params, sample_geographic_df
    ):
        """Test transformation service with inspection enabled."""
        service = TransformationService(enable_inspection=True)

        # Mock CSRSTransformer to avoid actual transformation
        with patch(
            "aco_camera_csv_converter.services.CSRSTransformer"
        ) as mock_transformer_class:
            mock_transformer = Mock()
            mock_transformer.t_coords = CoordType.UTM10
            mock_transformer.s_ref_frame = Reference.WGS84
            mock_transformer.s_coords = CoordType.GEOG
            mock_transformer.s_epoch = 2020.0
            mock_transformer.t_ref_frame = Reference.NAD83CSRS
            mock_transformer.t_epoch = 2002.0
            mock_transformer.return_value = [
                (500000.0, 6000000.0, 100.0),
                (501000.0, 6001000.0, 150.0),
            ]
            mock_transformer_class.return_value = mock_transformer

            with patch("aco_camera_csv_converter.services.sync_missing_grid_files"):
                service.transform_coordinates(
                    sample_geographic_df,
                    sample_transformation_params,
                    coord_type="dd",
                    should_transform=True,
                )

        # Should have inspection data
        inspection_data = service.inspect_transformation_input()
        assert inspection_data is not None
        assert inspection_data["coordinate_type"] == "dd"
        assert inspection_data["num_coordinates"] == 2
        assert inspection_data["source_reference_frame"] == "WGS84"
        assert inspection_data["target_reference_frame"] == "NAD83CSRS"

    def test_no_transformation_mode(self, sample_geographic_df):
        """Test transformation service with should_transform=False."""
        service = TransformationService(enable_inspection=True)

        result = service.transform_coordinates(
            sample_geographic_df,
            transformation_params=None,  # Not used when should_transform=False
            coord_type="dd",
            should_transform=False,
        )

        # Should return preprocessed DataFrame without transformation
        assert isinstance(result, pl.DataFrame)
        assert "RGBI_Filename" in result.columns
        assert "RGB_Filename" in result.columns

        # Should have no inspection data since no transformation occurred
        assert service.inspect_transformation_input() is None
