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
    coord_type: Literal["dms", "dd"] = "dd",
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
        .str.replace_all(".iiq", f"_rgbi.tif", literal=True)
        .alias("RGBI_Filename"),
        pl.col("Filename")
        .str.replace_all(".iiq", f"_cal.tif", literal=True)
        .alias("RGB_Filename"),
    )

    if not should_transform:
        return df

    transformer = CSRSTransformer(**kwargs)

    def _do_convert(s):
        lat, lon, alt = (
            s.struct.field("Origin (Latitude[deg]"),
            s.struct.field("Longitude[deg]"),
            s.struct.field("Altitude[m])"),
        )
        return pl.Series(list(transformer(list(zip(lon, lat, alt)))))

    df = df.with_columns(
        pl.struct(["Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])"])
        .map_batches(_do_convert, is_elementwise=True)
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


def get_coord_type(df: pl.DataFrame) -> Literal["dms", "dd"]:
    if df["Origin (Latitude[deg]"].str.contains("°").any():
        return "dms"
    return "dd"
