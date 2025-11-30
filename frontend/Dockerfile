FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to not create virtual environments (install system-wide in container)
RUN poetry config virtualenvs.create false

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies via Poetry
RUN poetry install --no-interaction --no-ansi --no-root

# Copy frontend code
COPY frontend ./frontend

# Expose Streamlit port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "frontend/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
