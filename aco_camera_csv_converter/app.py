import polars as pl
import streamlit as st
from csrspy.enums import CoordType

from aco_camera_csv_converter.consts import (
    REQUIRED_FILE_COLS,
    VERTICAL_DATUM_OPTS,
    REFERENCE_FRAME_OPTS,
    COORD_TYPE_OPTS,
)
from aco_camera_csv_converter.lib import to_decimal_year, convert_coords, get_coord_type


def _get_params(col, title: str, prefix: str) -> dict:
    """Render Source/Target transformation parameters in Streamlit."""
    col.write(f"### {title}")
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


st.title("ACO Camera Reference Converter")

# File upload
file = st.file_uploader("Riegel Camera Locations", type="csv")
if file:
    df = pl.read_csv(file, encoding="iso-8859-1")
    missing_cols = set(REQUIRED_FILE_COLS) - set(df.columns)
    if missing_cols:
        st.error(f"Missing columns in uploaded file: {list(missing_cols)}")
        st.stop()
    st.session_state.src_df = df
    with st.expander("View uploaded file"):
        st.dataframe(df)

image_type = st.radio(
    "Imagery Type",
    ["RGBI", "RGB"],
    horizontal=True,
    help='Determines the extension of the converted "Filename".',
)
should_transform = st.toggle("Transform coordinates?", value=True)

if should_transform:
    st.write("## Transform Parameters")
    col1, col2 = st.columns(2, gap="medium")
    src_params = _get_params(col1, "Source", "s")
    target_params = _get_params(col2, "Target", "t")
else:
    src_params = target_params = {}

if st.button(
    "Convert", disabled=(file is None), type="primary", use_container_width=True
):
    st.session_state.converted_df = convert_coords(
        st.session_state.src_df,
        coord_type=(get_coord_type(st.session_state.src_df)),
        image_type=image_type.lower(),
        should_transform=should_transform,
        **src_params,
        **target_params,
    )
    st.success("Conversion complete!")
    st.dataframe(st.session_state.converted_df)
