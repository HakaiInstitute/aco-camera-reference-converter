# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit web application for converting coordinates in Riegel Camera Locations CSV files. The application uses the `csrspy` library to perform Canadian Spatial Reference System transformations on camera location data.

## Core Architecture

- **`aco_camera_csv_converter/app.py`**: Main Streamlit application entry point
- **`aco_camera_csv_converter/models.py`**: Data models for transformation parameters and coordinate data
- **`aco_camera_csv_converter/services.py`**: Core coordinate transformation logic and inspection capabilities  
- **`aco_camera_csv_converter/ui.py`**: Streamlit UI components for parameter input and result display
- **`aco_camera_csv_converter/consts.py`**: Constants for reference frames, vertical datums, and required CSV columns
- **`aco_camera_csv_converter/lib.py`**: Legacy conversion functions (can be removed after migration)

The application is now modular with separate concerns:
- **Models**: Type-safe data structures for transformation parameters and coordinate data
- **Services**: Testable business logic with inspection capabilities for CSRSPY Transformer inputs
- **UI**: Reusable Streamlit components for consistent interface
- **App**: Main application orchestration

### Inspection Features

The `TransformationService` provides inspection capabilities to examine exactly what data is being passed to the CSRSPY Transformer:
- Log transformation parameters and coordinate data
- Display transformation summary in the UI  
- Access inspection data programmatically via `transformation_service.inspect_transformation_input()`

## Development Commands

### Running the Application
```bash
# Local development
uv run streamlit run aco_camera_csv_converter/app.py

# Docker development
docker compose up --build
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add development dependency
uv add --group dev <package-name>
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py

# Run tests with coverage
uv run pytest --cov=aco_camera_csv_converter
```

## Key Dependencies

- **streamlit**: Web application framework
- **polars**: DataFrame operations for CSV processing
- **csrspy**: Canadian Spatial Reference System transformations
- **uv**: Package manager and project management

## Docker Deployment

The application is containerized and configured to run on port 8501. Streamlit configuration is copied from the `streamlit/` directory during build.