# Makefile para o projeto DefiSys

# Define o interpretador Python a ser usado (o do ambiente virtual)
PYTHON = venv/bin/python

# Comando padrão, executado se você digitar apenas "make"
default: run

# Instala as dependências do projeto
install:
	pip install -r requirements.txt

# Roda a aplicação principal
run:
	$(PYTHON) -m backend.src.main

# Limpa arquivos temporários do Python
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Um alvo "phony" diz ao Make que 'run' não é um arquivo, mas sim um comando
.PHONY: default install run clean
