FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# requirements na raiz de backend/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia o código mantendo a estrutura backend/src
COPY src/ ./src
# se tiver a pasta data com o sqlite, copie também:
# COPY data/ ./data

# entra em src para rodar o app
WORKDIR /backend/src

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
