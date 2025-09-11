# Makefile para o projeto DefiSys com Poetry

# --- GERENCIAMENTO DE DEPENDÊNCIAS ---

# Instala as dependências do projeto usando o Poetry
install:
	poetry install

# --- EXECUÇÃO E TESTES ---

# Roda a aplicação principal
run:
	poetry run python -m backend.src.main

# (Alvo para futuros testes com pytest)
test:
	poetry run pytest

# --- QUALIDADE DE CÓDIGO ---

# Verifica o código por erros e problemas de estilo com Ruff
lint:
	poetry run ruff check .

# Formata o código automaticamente com Black e Ruff
format:
	poetry run ruff format .
	poetry run black .

# --- EXECUÇÃO DO FRONTEND E BACKEND ---
run-api:
	poetry run uvicorn backend.src.api:app --reload --host 0.0.0.0

run-frontend:
	poetry run streamlit run frontend/dashboard.py
	

# --- LIMPEZA ---

# Limpa arquivos temporários do Python e bancos de dados
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.db" -delete

# --- CONFIGURAÇÃO ---

# Um alvo "phony" diz ao Make que estes não são arquivos, mas sim comandos
.PHONY: install run test lint format clean