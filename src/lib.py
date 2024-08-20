import logging
import time
from datetime import datetime as dt
from typing import Literal

import polars as pl
import pyproj.sync
from csrspy import CSRSTransformer

logger = logging.getLogger(__name__)


def sync_missing_grid_files():
    target_directory = pyproj.sync.get_user_data_dir(True)
    endpoint = pyproj.sync.get_proj_endpoint()
    grids = pyproj.sync.get_transform_grid_list(area_of_use="Canada")

    if len(grids):
        logger.info("Syncing PROJ grid files.")

    for grid in grids:
        filename = grid["properties"]["name"]
        pyproj.sync._download_resource_file(
            file_url=f"{endpoint}/{filename}",
            short_name=filename,
            directory=target_directory,
            sha256=grid["properties"]["sha256sum"],
        )


def to_decimal_year(date: dt) -> float:
    year = date.year
    start_of_this_year = dt(year=year, month=1, day=1)
    start_of_next_year = dt(year=year + 1, month=1, day=1)
    year_elapsed = time.mktime(date.timetuple()) - time.mktime(
        start_of_this_year.timetuple()
    )
    year_duration = time.mktime(start_of_next_year.timetuple()) - time.mktime(
        start_of_this_year.timetuple()
    )
    return year + year_elapsed / year_duration


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
    rename_only: bool = False,
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
        pl.col("Filename").str.replace_all(".iiq", "_rgbi.tif", literal=True)
    )

    if rename_only:
        return df

    transformer = CSRSTransformer(**kwargs)

    def _do_convert(s):
        lat, lon, alt = (
            s.struct.field("Origin (Latitude[deg]"),
            s.struct.field("Longitude[deg]"),
            s.struct.field("Altitude[m])"),
        )
        return pl.Series(list(transformer(list(zip(lon, lat, alt)))))

    return (
        df.with_columns(
            pl.struct(["Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])"])
            .map_batches(_do_convert, is_elementwise=True)
            .alias("converted"),
        )
        .drop("Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])")
        .with_columns(
            pl.col("converted").list.get(0).alias("Origin(Easting[m]"),
            pl.col("converted").list.get(1).alias("Northing[m]"),
            pl.col("converted").list.get(2).alias("Altitude[m])"),
        )
        .select(
            "Timestamp",
            "Filename",
            "Origin(Easting[m]",
            "Northing[m]",
            "Altitude[m])",
            "Roll(X)[deg]",
            "Pitch(Y)[deg]",
            "Yaw(Z)[deg]",
            "Omega[deg]",
            "Phi[deg]",
            "Kappa[deg]",
        )
    )
