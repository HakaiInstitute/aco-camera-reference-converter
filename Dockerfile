FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Create config folder and configuration file
RUN mkdir -p /root/.streamlit
RUN echo "\
[browser]\n\
gatherUsageStats = false\n\
\n\
[client]\n\
showErrorDetails = true\n\
toolbarMode = 'viewer'\n\
\n\
[server]\n\
enableCORS = true\n\
enableXsrfProtection = true\n\
\n\
[theme]\n\
base='dark'\n\
" > /root/.streamlit/config.toml

# Create credentials file to disable telemetry
RUN echo "\
[general]\n\
email = ''\n\
" > /root/.streamlit/credentials.toml

# Set environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

# Expose port
EXPOSE 8501

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Command to run the Streamlit app
CMD ["python", "-m", "streamlit", "run", "aco_camera_csv_converter/app.py", "--server.address", "0.0.0.0"]