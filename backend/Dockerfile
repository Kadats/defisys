FROM python:3.12-slim

WORKDIR /app

# Install git for git dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend ./backend

# Expose FastAPI port
EXPOSE 8000

# Run the application
# Copy entrypoint script
COPY backend/entrypoint.sh .
RUN chmod +x entrypoint.sh

# Run the application via entrypoint
CMD ["./entrypoint.sh"]
