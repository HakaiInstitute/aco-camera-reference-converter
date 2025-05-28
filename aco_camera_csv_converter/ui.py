import streamlit as st
from csrspy.enums import CoordType
from csrspy.utils import date_to_decimal_year

from consts import (
    COORD_TYPE_OPTS,
    REFERENCE_FRAME_OPTS,
    VERTICAL_DATUM_OPTS,
)
from models import TransformationParameters


class TransformationParametersUI:
    """Handles UI for transformation parameters input."""

    @staticmethod
    def render_parameters(col, title: str, prefix: str) -> TransformationParameters:
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

        # Handle epoch input differently for source vs target
        if prefix == "s":
            epoch = col.date_input(f"{title} Epoch", key=f"{prefix}_epoch")
            epoch_value = date_to_decimal_year(epoch)
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

        # Handle coordinate type conversion
        if coords == "Projected":
            coord_type = list(CoordType)[utm_zone - 1]
        elif coords == "Cartesian":
            coord_type = CoordType.CART
        else:
            coord_type = CoordType.GEOG

        # Use the user's selected reference frame and vertical datum
        ref_frame_val = ref_frame[1]
        vd_val = vertical_datum[1]

        # Return appropriate parameters based on prefix
        if prefix == "s":
            return {
                "s_ref_frame": ref_frame_val,
                "s_coords": coord_type,
                "s_vd": vd_val,
                "s_epoch": epoch_value,
            }
        else:
            return {
                "t_ref_frame": ref_frame_val,
                "t_coords": coord_type,
                "t_vd": vd_val,
                "t_epoch": epoch_value,
            }


class FileValidationUI:
    """Handles file upload and validation UI."""

    @staticmethod
    def validate_and_display_file(df, required_cols_geo, required_cols_cart):
        """Validate uploaded file and display appropriate messages."""
        missing_cols_geo = set(required_cols_geo) - set(df.columns)
        missing_cols_cart = set(required_cols_cart) - set(df.columns)

        if missing_cols_geo and missing_cols_cart:
            st.error(
                f"Missing columns in uploaded file. Expected either:\n"
                f"Geographic: {list(missing_cols_geo)}\n"
                f"Or Cartesian: {list(missing_cols_cart)}"
            )
            st.stop()

        return True


class InspectionUI:
    """Handles transformation inspection display."""

    @staticmethod
    def display_transformation_summary(transformation_summary: dict):
        """Display transformation input summary in an expander."""
        with st.expander("🔍 Transformation Details"):
            st.write("**Source Parameters:**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(
                    f"- Reference Frame: {transformation_summary['source_reference_frame']}"
                )
                st.write(
                    f"- Coordinate Type: {transformation_summary['source_coord_type']}"
                )
                st.write(
                    f"- Vertical Datum: {transformation_summary['source_vertical_datum']}"
                )
                st.write(f"- Epoch: {transformation_summary['source_epoch']}")

            with col2:
                st.write("**Target Parameters:**")
                st.write(
                    f"- Reference Frame: {transformation_summary['target_reference_frame']}"
                )
                st.write(
                    f"- Coordinate Type: {transformation_summary['target_coord_type']}"
                )
                st.write(
                    f"- Vertical Datum: {transformation_summary['target_vertical_datum']}"
                )
                st.write(f"- Epoch: {transformation_summary['target_epoch']}")

            st.write("**Coordinate Data:**")
            st.write(f"- Input Format: {transformation_summary['coordinate_type']}")
            st.write(f"- Number of Points: {transformation_summary['num_coordinates']}")

            if transformation_summary["first_coordinate"]:
                st.write(
                    f"- First Coordinate: {transformation_summary['first_coordinate']}"
                )
            if transformation_summary["last_coordinate"]:
                st.write(
                    f"- Last Coordinate: {transformation_summary['last_coordinate']}"
                )
