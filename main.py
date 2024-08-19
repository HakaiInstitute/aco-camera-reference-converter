import time
from datetime import datetime as dt
from typing import Literal

import polars as pl
import streamlit as st
from csrspy import CSRSTransformer
from csrspy.enums import Reference, VerticalDatum, CoordType

# Constants
REQUIRED_FILE_COLS = [
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
]

VERTICAL_DATUM_OPTS = [
    ("WGS84", VerticalDatum.WGS84),
    ("GRS80", VerticalDatum.GRS80),
    ("CGG2013a", VerticalDatum.CGG2013A),
    ("CGG2013", VerticalDatum.CGG2013),
    ("HT2_2010v70", VerticalDatum.HT2_2010v70),
]

REFERENCE_FRAME_OPTS = [
    ("WGS84", Reference.WGS84),
    ("NAD83 (CSRS)", Reference.NAD83CSRS),
    ("ITRF1988", Reference.ITRF88),
    ("ITRF1989", Reference.ITRF89),
    ("ITRF1990", Reference.ITRF90),
    ("ITRF1991", Reference.ITRF91),
    ("ITRF1992", Reference.ITRF92),
    ("ITRF1993", Reference.ITRF93),
    ("ITRF1994", Reference.ITRF94),
    ("ITRF1996", Reference.ITRF96),
    ("ITRF1997", Reference.ITRF97),
    ("ITRF2000", Reference.ITRF00),
    ("ITRF2005", Reference.ITRF05),
    ("ITRF2008", Reference.ITRF08),
    ("ITRF2014", Reference.ITRF14),
    ("ITRF2020", Reference.ITRF20),
]

COORD_TYPE_OPTS = ["Geographic", "Projected"]


# Helper functions
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

    def convert(s):
        lat, lon, alt = (
            s.struct.field("Origin (Latitude[deg]"),
            s.struct.field("Longitude[deg]"),
            s.struct.field("Altitude[m])"),
        )
        return pl.Series(list(transformer(list(zip(lon, lat, alt)))))

    return (
        df.with_columns(
            pl.struct(["Origin (Latitude[deg]", "Longitude[deg]", "Altitude[m])"])
            .map_batches(convert, is_elementwise=True)
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


# Streamlit app
def main():
    st.title("ACO Camera Reference Converter")

    # File upload
    file = st.file_uploader("Riegel Camera Locations CSV (WGS84)", type="csv")
    if file:
        df = pl.read_csv(file, encoding="iso-8859-1")
        missing_cols = set(REQUIRED_FILE_COLS) - set(df.columns)
        if missing_cols:
            st.error(f"Missing columns in uploaded file: {list(missing_cols)}")
            st.stop()
        st.session_state.src_df = df
        with st.expander("View uploaded file"):
            st.dataframe(df)

    rename_only = st.checkbox('Just rename "Filename" column', value=False)

    if not rename_only:
        col1, col2 = st.columns(2, gap="medium")
        src_params = get_params(col1, "Source", "s")
        target_params = get_params(col2, "Target", "t")
    else:
        src_params = target_params = {}

    if st.button(
        "Convert", disabled=(file is None), type="primary", use_container_width=True
    ):
        converted_df = convert_coords(
            st.session_state.src_df,
            coord_type="dms"
            if st.session_state.src_df["Origin (Latitude[deg]"].str.contains("°").any()
            else "dd",
            rename_only=rename_only,
            **{
                k: v
                for k, v in {**src_params, **target_params}.items()
                if k != "rename_only"
            },
        )
        st.session_state.converted_df = converted_df
        st.success("Conversion complete!")
        st.dataframe(converted_df)


def get_params(col, title: str, prefix: str) -> dict:
    col.write(f"## {title}")
    ref_frame = col.selectbox(
        f"{title} Reference Frame",
        REFERENCE_FRAME_OPTS,
        format_func=lambda x: x[0],
        key=f"{prefix}_ref_frame",
    )
    coords = col.selectbox(
        f"{title} Coordinate Type", COORD_TYPE_OPTS, key=f"{prefix}_coords"
    )
    utm_zone = col.number_input(
        f"{title} UTM Zone",
        min_value=3,
        max_value=23,
        value=10,
        disabled=coords != "Projected",
        key=f"{prefix}_utm_zone",
    )
    vertical_datum = col.selectbox(
        f"{title} Vertical Datum",
        VERTICAL_DATUM_OPTS,
        format_func=lambda x: x[0],
        key=f"{prefix}_vd",
    )

    if prefix == "s":
        epoch = col.date_input(f"{title} Epoch", key=f"{prefix}_epoch")
        epoch_value = to_decimal_year(epoch)
    else:
        epoch_value = col.number_input(
            f"{title} Epoch",
            min_value=1900.0,
            max_value=3000.0,
            value=2002.0,
            step=1.0,
            format="%.1f",
            key=f"{prefix}_epoch",
        )

    return {
        f"{prefix}_ref_frame": ref_frame[1],
        f"{prefix}_coords": list(CoordType)[utm_zone - 1]
        if coords == "Projected"
        else CoordType.GEOG,
        f"{prefix}_vd": vertical_datum[1],
        f"{prefix}_epoch": epoch_value,
    }


if __name__ == "__main__":
    main()
