import logging
from typing import List, Tuple, Literal, Optional
import polars as pl
from csrspy import CSRSTransformer
from csrspy.enums import CoordType
from csrspy.utils import sync_missing_grid_files

from models import (
    TransformationParameters,
    CoordinateData,
    TransformationInput,
)

logger = logging.getLogger(__name__)


class CoordinateProcessor:
    """Handles coordinate data preprocessing and format detection."""

    @staticmethod
    def dms_to_decimal(dms_str: str) -> float:
        """Convert DMS string to decimal degrees."""
        direction = dms_str[0]
        parts = dms_str[1:].replace('"', "").split("° ")
        degrees = float(parts[0])
        minutes, seconds = map(float, parts[1].split("' "))
        decimal = degrees + minutes / 60 + seconds / 3600
        return -decimal if direction in ["S", "W"] else decimal

    @staticmethod
    def detect_coord_type(df: pl.DataFrame) -> Literal["dms", "dd", "cart"]:
        """Detect coordinate type from DataFrame columns."""
        # Check if file has cartesian coordinates
        if (
            "Origin (X[m]" in df.columns
            and "Y[m]" in df.columns
            and "Z[m])" in df.columns
        ):
            return "cart"
        # Check if geographic coordinates are in DMS format
        elif (
            "Origin (Latitude[deg]" in df.columns
            and df["Origin (Latitude[deg]"].dtype == pl.String
            and df["Origin (Latitude[deg]"].str.contains("°").any()
        ):
            return "dms"
        return "dd"

    @staticmethod
    def preprocess_dataframe(
        df: pl.DataFrame, coord_type: Literal["dms", "dd", "cart"]
    ) -> pl.DataFrame:
        """Preprocess DataFrame to normalize coordinate formats."""
        processed_df = df.clone()

        # Convert DMS to decimal if needed
        if coord_type == "dms":
            processed_df = processed_df.with_columns(
                pl.col("Origin (Latitude[deg]").map_elements(
                    CoordinateProcessor.dms_to_decimal, return_dtype=pl.Float64
                ),
                pl.col("Longitude[deg]").map_elements(
                    CoordinateProcessor.dms_to_decimal, return_dtype=pl.Float64
                ),
            )

        # Add filename transformations
        processed_df = processed_df.with_columns(
            pl.col("Filename")
            .str.replace_all(".iiq", "_rgbi.tif", literal=True)
            .alias("RGBI_Filename"),
            pl.col("Filename")
            .str.replace_all(".iiq", "_cal.tif", literal=True)
            .alias("RGB_Filename"),
        )

        return processed_df

    @staticmethod
    def extract_coordinates(
        df: pl.DataFrame, coord_type: Literal["dms", "dd", "cart"]
    ) -> List[Tuple[float, float, float]]:
        """Extract coordinate tuples from DataFrame."""
        if coord_type == "cart":
            return list(
                zip(
                    df["Origin (X[m]"].to_list(),
                    df["Y[m]"].to_list(),
                    df["Z[m])"].to_list(),
                )
            )
        else:
            # For geographic coordinates, return as (lon, lat, alt) for CSRSTransformer
            return list(
                zip(
                    df["Longitude[deg]"].to_list(),
                    df["Origin (Latitude[deg]"].to_list(),
                    df["Altitude[m])"].to_list(),
                )
            )


class TransformationService:
    """Handles coordinate transformations with inspection capabilities."""

    def __init__(self, enable_inspection: bool = True):
        self.enable_inspection = enable_inspection
        self.last_transformation_input: Optional[TransformationInput] = None

    def inspect_transformation_input(self) -> Optional[dict]:
        """Get inspection data for the last transformation."""
        if self.last_transformation_input is None:
            return None
        return self.last_transformation_input.get_summary()

    def transform_coordinates(
        self,
        df: pl.DataFrame,
        transformation_params: TransformationParameters,
        coord_type: Optional[Literal["dms", "dd", "cart"]] = None,
        should_transform: bool = True,
    ) -> pl.DataFrame:
        """Transform coordinates with inspection capabilities."""
        # Ensure grid files are available
        sync_missing_grid_files()

        # Auto-detect coordinate type if not provided
        if coord_type is None:
            coord_type = CoordinateProcessor.detect_coord_type(df)

        # Preprocess the dataframe
        processed_df = CoordinateProcessor.preprocess_dataframe(df, coord_type)

        # Return early if no transformation is needed
        if not should_transform:
            return processed_df

        # Extract coordinates for transformation
        coordinates = CoordinateProcessor.extract_coordinates(processed_df, coord_type)
        coordinate_data = CoordinateData(coord_type=coord_type, coordinates=coordinates)

        # Store transformation input for inspection
        if self.enable_inspection:
            self.last_transformation_input = TransformationInput(
                transformation_params=transformation_params,
                coordinate_data=coordinate_data,
                original_df=df,
            )

            # Log transformation details
            summary = self.last_transformation_input.get_summary()
            logger.info(f"Transformation Input Summary: {summary}")

        # Create and configure transformer
        transformer = CSRSTransformer(**transformation_params.to_csrspy_kwargs())

        # Log transformer configuration
        if self.enable_inspection:
            logger.info("CSRSTransformer configured with:")
            logger.info(
                f"  Source: {transformer.s_ref_frame.name} ({transformer.s_coords.name}) @ {transformer.s_epoch}"
            )
            logger.info(
                f"  Target: {transformer.t_ref_frame.name} ({transformer.t_coords.name}) @ {transformer.t_epoch}"
            )
            logger.info(f"  Processing {len(coordinates)} coordinate points")

        # Perform transformation
        transformed_coords = list(transformer(coordinates))

        # Log sample results
        if self.enable_inspection and transformed_coords:
            logger.info("Sample transformation result:")
            logger.info(f"  Input:  {coordinates[0]}")
            logger.info(f"  Output: {transformed_coords[0]}")

        # Apply transformed coordinates back to dataframe
        return self._apply_transformed_coordinates(
            processed_df, transformed_coords, transformer.t_coords, coord_type
        )

    def _apply_transformed_coordinates(
        self,
        df: pl.DataFrame,
        transformed_coords: List[Tuple[float, float, float]],
        target_coord_type: CoordType,
        original_coord_type: Literal["dms", "dd", "cart"],
    ) -> pl.DataFrame:
        """Apply transformed coordinates back to the DataFrame."""
        # Convert to polars Series
        coords_series = pl.Series("converted", transformed_coords)
        df_with_coords = df.with_columns(coords_series)

        # Remove original coordinate columns
        if original_coord_type == "cart":
            df_with_coords = df_with_coords.drop("Origin (X[m]", "Y[m]", "Z[m])")
        else:
            df_with_coords = df_with_coords.drop(
                "Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])"
            )

        # Add new coordinate columns based on target type
        if target_coord_type == CoordType.GEOG:
            return df_with_coords.with_columns(
                pl.col("converted").list.get(1).alias("Origin (Latitude[deg]"),
                pl.col("converted").list.get(0).alias("Longitude[deg]"),
                pl.col("converted").list.get(2).alias("Altitude[m])"),
            ).select(
                "Timestamp",
                "Filename",
                "Origin (Latitude[deg]",
                "Longitude[deg]",
                "Altitude[m])",
                "Roll(X)[deg]",
                "Pitch(Y)[deg]",
                "Yaw(Z)[deg]",
                "Omega[deg]",
                "Phi[deg]",
                "Kappa[deg]",
            )
        elif target_coord_type == CoordType.CART:
            return df_with_coords.with_columns(
                pl.col("converted").list.get(0).alias("Origin (X[m]"),
                pl.col("converted").list.get(1).alias("Y[m]"),
                pl.col("converted").list.get(2).alias("Z[m])"),
            ).select(
                "Timestamp",
                "RGBI_Filename",
                "RGB_Filename",
                "Origin (X[m]",
                "Y[m]",
                "Z[m])",
                "Omega[deg]",
                "Phi[deg]",
                "Kappa[deg]",
                "Roll(X)[deg]",
                "Pitch(Y)[deg]",
                "Yaw(Z)[deg]",
            )
        else:  # Projected coordinates
            return df_with_coords.with_columns(
                pl.col("converted").list.get(0).alias("Easting[m]"),
                pl.col("converted").list.get(1).alias("Northing[m]"),
                pl.col("converted").list.get(2).alias("Altitude[m]"),
            ).select(
                "Timestamp",
                "RGBI_Filename",
                "RGB_Filename",
                "Easting[m]",
                "Northing[m]",
                "Altitude[m]",
                "Omega[deg]",
                "Phi[deg]",
                "Kappa[deg]",
                "Roll(X)[deg]",
                "Pitch(Y)[deg]",
                "Yaw(Z)[deg]",
            )


# Global service instance for the app
transformation_service = TransformationService(enable_inspection=True)
