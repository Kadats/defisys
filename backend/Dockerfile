FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PostgreSQL (libpq-dev) and compilation (gcc)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to not create virtual environments (install system-wide in container)
RUN poetry config virtualenvs.create false

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock README.md ./

# Install Python dependencies via Poetry
RUN poetry install --no-interaction --no-ansi --no-root

# Copy backend code
COPY backend ./backend

# Install the project itself (if it's a package)
RUN poetry install --no-interaction --no-ansi --only-root

# Expose FastAPI port
EXPOSE 8000

# Copy entrypoint script
COPY backend/entrypoint.sh .
RUN chmod +x entrypoint.sh

# Run the application via entrypoint
CMD ["./entrypoint.sh"]
