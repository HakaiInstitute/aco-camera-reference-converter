import logging
from typing import Literal

import polars as pl
from csrspy import CSRSTransformer
from csrspy.enums import CoordType
from csrspy.utils import sync_missing_grid_files

logger = logging.getLogger(__name__)


def dms_to_decimal(dms_str: str) -> float:
    direction = dms_str[0]
    parts = dms_str[1:].replace('"', "").split("° ")
    degrees = float(parts[0])
    minutes, seconds = map(float, parts[1].split("' "))
    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if direction in ["S", "W"] else decimal


def convert_coords(
    df: pl.DataFrame,
    coord_type: Literal["dms", "dd", "cart"] = "dd",
    should_transform: bool = True,
    **kwargs,
) -> pl.DataFrame:
    sync_missing_grid_files()

    if coord_type == "dms":
        df = df.with_columns(
            pl.col("Origin (Latitude[deg]").map_elements(
                dms_to_decimal, return_dtype=pl.Float64
            ),
            pl.col("Longitude[deg]").map_elements(
                dms_to_decimal, return_dtype=pl.Float64
            ),
        )

    df = df.with_columns(
        pl.col("Filename")
        .str.replace_all(".iiq", "_rgbi.tif", literal=True)
        .alias("RGBI_Filename"),
        pl.col("Filename")
        .str.replace_all(".iiq", "_cal.tif", literal=True)
        .alias("RGB_Filename"),
    )

    if not should_transform:
        return df

    transformer = CSRSTransformer(**kwargs)

    if coord_type == "cart":
        # Handle cartesian input coordinates
        def _do_convert_cart(s):
            x, y, z = (
                s.struct.field("Origin (X[m]"),
                s.struct.field("Y[m]"),
                s.struct.field("Z[m])"),
            )
            return pl.Series(list(transformer(list(zip(x, y, z)))))

        df = df.with_columns(
            pl.struct(["Origin (X[m]", "Y[m]", "Z[m])"])
            .map_batches(_do_convert_cart, is_elementwise=True)
            .alias("converted"),
        ).drop("Origin (X[m]", "Y[m]", "Z[m])")
    else:
        # Handle geographic input coordinates
        def _do_convert_geo(s):
            lat, lon, alt = (
                s.struct.field("Origin (Latitude[deg]"),
                s.struct.field("Longitude[deg]"),
                s.struct.field("Altitude[m])"),
            )
            return pl.Series(list(transformer(list(zip(lon, lat, alt)))))

        df = df.with_columns(
            pl.struct(["Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])"])
            .map_batches(_do_convert_geo, is_elementwise=True)
            .alias("converted"),
        ).drop("Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])")

    if transformer.t_coords == CoordType.GEOG:
        df = df.with_columns(
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
    elif transformer.t_coords == CoordType.CART:
        df = df.with_columns(
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
    else:
        df = df.with_columns(
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

    return df


def get_coord_type(df: pl.DataFrame) -> Literal["dms", "dd", "cart"]:
    # Check if file has cartesian coordinates
    if "Origin (X[m]" in df.columns and "Y[m]" in df.columns and "Z[m])" in df.columns:
        return "cart"
    # Check if geographic coordinates are in DMS format
    elif (
        "Origin (Latitude[deg]" in df.columns
        and df["Origin (Latitude[deg]"].dtype == pl.String
        and df["Origin (Latitude[deg]"].str.contains("°").any()
    ):
        return "dms"
    return "dd"
