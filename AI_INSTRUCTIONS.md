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
* O Frontend (Vue.js) NUNCA deve fazer cálculos de lógica de negócios, ROI, ou PnL. Ele apenas exibe os dados.
* O Backend (Python) é a única fonte da verdade. Todos os cálculos financeiros ocorrem no servidor ou no banco de dados.

## 3. Padrões de Código Python
* Use tipagem estrita (Type Hints) em todas as funções.
* Nunca use `print()`. Use sempre o logger configurado do sistema (`logger.info`, `logger.error`).
* Ao lidar com DataFrames do Pandas, trate ativamente a possibilidade de dados vazios (`df.empty`) e valores nulos (`NaN`) gerados por falta de histórico de APIs externas.

## 4. Regras de Negócio (Trading)
* Estratégias nunca devem alocar 100% do capital (All-in) em uma única entrada.
* Respeite sempre a variável de cooldown de operações para evitar over-trading.

## 5. Integração com Google Gemini API
* **Versão da Biblioteca:** Use `google-generativeai >= 0.7.2` (versões antigas como 0.4.1 têm bugs e podem causar NotFound em modelos recentes).
* **Modelo Recomendado:** Use `models/gemini-2.0-flash` (JSON estável com `response_mime_type` e ~1500 RPD no tier gratuito).
* **Nota Arquitetural:** O modelo `gemini-2.5-flash` possui hard-limit de apenas 20 requisições/dia no tier gratuito, inviabilizando simulações de backtest de 30 dias (~180 requisições). O modelo `gemini-1.5-flash` foi descontinuado pela Google. O `gemini-2.0-flash` suporta ~1500 requisições/dia, tornando-o adequado para testes extensivos (até 250 dias de histórico ou 8+ backtests de 30 dias por dia).
* **Fallback de Modelo:** Se `models/gemini-2.0-flash` não estiver disponível, o sistema tentará `models/gemini-flash-latest` e depois `models/gemini-2.5-flash`.
* **Override por Env:** Para trocar o modelo sem alterar código, defina `GEMINI_MODEL=gemini-2.0-flash` no seu `.env`.
* **Configuração:** Use `genai.configure(api_key=..., transport="rest")` para evitar truncamento em gRPC e configure `GenerationConfig` (temperature, max_output_tokens) durante a inicialização do modelo via `GenerativeModel()`.
* **Rate Limiting:** A API gratuita do Gemini tem limite de 15 RPM (requests por minuto). SEMPRE implemente delay entre chamadas usando `GEMINI_API_DELAY_SECONDS` (padrão: 5s). Isso garante máximo de 12 RPM, abaixo do limite de 15 RPM. Para simulações de 30 dias (180 candles de 4h), o tempo total será ~15 minutos (180 × 5s).
* **Retry com Backoff:** Implemente retry exponencial (2s, 4s, 8s) para erros 429 (TooManyRequests). Após 3 tentativas falhadas, caia para fallback heurístico.
* **Fallback Obrigatório:** Sempre implemente fallback heurístico quando a API Gemini falhar. O projeto não pode depender exclusivamente de APIs externas.
* **Logging de Erros:** Log erros da API com `logger.error()` incluindo o tipo de exceção completo e mensagem truncada (máximo 150 caracteres).
* **Validação de Resposta:** Sempre valide a resposta JSON antes de usar (verificar tipo dict, estrutura esperada, ranges de valores numéricos).

## 6. Seleção Dinâmica de Estratégias
* O sistema suporta múltiplas estratégias de trading via Strategy Pattern.
* **Estratégias Disponíveis:**
	* `accumulator` (padrão): Estratégia de acumulação gradual com DCA.
	* `btc_lite`: Estratégia simplificada baseada em condições de mercado.
	* `swing_usd` (em desenvolvimento): Estratégia de swing trading em USD.
* **API de Simulação:** O endpoint `POST /api/simulation/run` aceita o parâmetro `strategy_type` no corpo da requisição.
* **Implementação:** A função `run_simulation()` em `backend/src/system_runner.py` implementa uma Strategy Factory que instancia a estratégia correta baseada no parâmetro `strategy_type`.
* **Extensibilidade:** Para adicionar novas estratégias:
	1. Crie uma nova classe que herde de `BaseStrategy` em `backend/src/strategies/`.
	2. Implemente o método `execute()` com a lógica de trading.
	3. Adicione a estratégia ao `__init__.py` do módulo strategies.
	4. Atualize a Strategy Factory em `run_simulation()` para incluir o novo tipo.