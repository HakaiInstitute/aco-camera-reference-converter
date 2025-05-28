from dataclasses import dataclass
from typing import List, Tuple, Literal
import polars as pl
from csrspy.enums import CoordType, Reference, VerticalDatum


@dataclass
class TransformationParameters:
    """Parameters for coordinate transformation."""

    s_ref_frame: Reference
    s_coords: CoordType
    s_vd: VerticalDatum
    s_epoch: float
    t_ref_frame: Reference
    t_coords: CoordType
    t_vd: VerticalDatum
    t_epoch: float

    def to_csrspy_kwargs(self) -> dict:
        """Convert to kwargs for CSRSTransformer."""
        return {
            "s_ref_frame": self.s_ref_frame,
            "s_coords": self.s_coords,
            "s_vd": self.s_vd,
            "s_epoch": self.s_epoch,
            "t_ref_frame": self.t_ref_frame,
            "t_coords": self.t_coords,
            "t_vd": self.t_vd,
            "t_epoch": self.t_epoch,
        }


@dataclass
class CoordinateData:
    """Represents coordinate data for transformation."""

    coord_type: Literal["dms", "dd", "cart"]
    coordinates: List[Tuple[float, float, float]]

    def __post_init__(self):
        """Validate coordinate data."""
        if not self.coordinates:
            raise ValueError("Coordinates list cannot be empty")

        # Validate each coordinate tuple has 3 values
        for i, coord in enumerate(self.coordinates):
            if len(coord) != 3:
                raise ValueError(
                    f"Coordinate {i} must have exactly 3 values, got {len(coord)}"
                )


@dataclass
class TransformationInput:
    """Complete input data for transformation inspection."""

    transformation_params: TransformationParameters
    coordinate_data: CoordinateData
    original_df: pl.DataFrame

    def get_summary(self) -> dict:
        """Get a summary of transformation inputs for inspection."""
        return {
            "source_reference_frame": self.transformation_params.s_ref_frame.name,
            "source_coord_type": self.transformation_params.s_coords.name,
            "source_vertical_datum": self.transformation_params.s_vd.name,
            "source_epoch": self.transformation_params.s_epoch,
            "target_reference_frame": self.transformation_params.t_ref_frame.name,
            "target_coord_type": self.transformation_params.t_coords.name,
            "target_vertical_datum": self.transformation_params.t_vd.name,
            "target_epoch": self.transformation_params.t_epoch,
            "coordinate_type": self.coordinate_data.coord_type,
            "num_coordinates": len(self.coordinate_data.coordinates),
            "first_coordinate": self.coordinate_data.coordinates[0]
            if self.coordinate_data.coordinates
            else None,
            "last_coordinate": self.coordinate_data.coordinates[-1]
            if self.coordinate_data.coordinates
            else None,
        }
