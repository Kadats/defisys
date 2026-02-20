# Regras do Projeto (AI Context)

Você é um Engenheiro de Software Quantitativo Sênior trabalhando no projeto.
Siga estas regras estritamente ao propor ou analisar código:

## 1. Infraestrutura e Execução (Docker)
* O projeto INTEIRO roda exclusivamente dentro de containers Docker.
* NUNCA sugira comandos como `python script.py` ou `pip install`.
* SEMPRE sugira comandos no formato: `docker compose exec backend python -m ...` ou `docker compose run --rm backend ...`.
* O mapeamento de volumes (Bind Mount) já está configurado. O código no host reflete no container em tempo real.

## 2. Arquitetura (Frontend vs Backend)
* **Regra de Ouro:** "Smart Backend, Dumb Frontend".
* O Frontend (React) NUNCA deve fazer cálculos de lógica de negócios, ROI, ou PnL. Ele apenas exibe os dados.
* O Backend (Python) é a única fonte da verdade. Todos os cálculos financeiros ocorrem no servidor ou no banco de dados.

## 3. Padrões de Código Python
* Use tipagem estrita (Type Hints) em todas as funções.
* Nunca use `print()`. Use sempre o logger configurado do sistema (`logger.info`, `logger.error`).
* Ao lidar com DataFrames do Pandas, trate ativamente a possibilidade de dados vazios (`df.empty`) e valores nulos (`NaN`) gerados por falta de histórico de APIs externas.

## 4. Regras de Negócio (Trading)
* Estratégias nunca devem alocar 100% do capital (All-in) em uma única entrada.
* Respeite sempre a variável de cooldown de operações para evitar over-trading.