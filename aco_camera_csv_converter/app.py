import polars as pl
import streamlit as st
import logging

from aco_camera_csv_converter.consts import (
    REQUIRED_FILE_COLS_GEOGRAPHIC,
    REQUIRED_FILE_COLS_CARTESIAN,
)
from aco_camera_csv_converter.models import TransformationParameters
from aco_camera_csv_converter.services import (
    transformation_service,
    CoordinateProcessor,
)
from aco_camera_csv_converter.ui import (
    TransformationParametersUI,
    FileValidationUI,
    InspectionUI,
)

# Configure logging for inspection
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.title("ACO Camera Reference Converter")

# File upload
file = st.file_uploader("Riegel Camera Locations", type="csv")
if file:
    df = pl.read_csv(file, encoding="iso-8859-1")

    # Validate file structure
    FileValidationUI.validate_and_display_file(
        df, REQUIRED_FILE_COLS_GEOGRAPHIC, REQUIRED_FILE_COLS_CARTESIAN
    )

    st.session_state.src_df = df
    with st.expander("View uploaded file"):
        st.dataframe(df)

name_only = st.toggle("Only update filenames", value=False)

# Transformation parameters UI
if not name_only:
    st.write("## Transform Parameters")
    col1, col2 = st.columns(2, gap="medium")

    src_params = TransformationParametersUI.render_parameters(col1, "Source", "s")
    target_params = TransformationParametersUI.render_parameters(col2, "Target", "t")

    # Combine parameters into TransformationParameters object
    transformation_params = TransformationParameters(**src_params, **target_params)

# Convert button and processing
if st.button(
    "Convert", disabled=(file is None), type="primary", use_container_width=True
):
    if name_only:
        # Just update filenames without transformation
        coord_type = CoordinateProcessor.detect_coord_type(st.session_state.src_df)
        st.session_state.converted_df = CoordinateProcessor.preprocess_dataframe(
            st.session_state.src_df, coord_type
        )
    else:
        # Perform full transformation
        st.session_state.converted_df = transformation_service.transform_coordinates(
            st.session_state.src_df, transformation_params, should_transform=True
        )

        # Display transformation inspection details
        transformation_summary = transformation_service.inspect_transformation_input()
        if transformation_summary:
            InspectionUI.display_transformation_summary(transformation_summary)

    st.success("Conversion complete!")
    st.dataframe(st.session_state.converted_df)
