# DefiSys - Sistema de Trading Automatizado com IA para DeFi

O **DefiSys** é um sistema inteligente de trading e provisão de liquidez (LP) focado em Bitcoin. Ele utiliza Machine Learning para identificar regimes de mercado e executa estratégias complexas de DeFi (como loops de alavancagem na AAVE e LPs concentradas na Uniswap v3) para maximizar o retorno e acumular ativos.

## 🧠 O Cérebro (Arquitetura)

O sistema opera em um ciclo contínuo de coleta, análise e execução:

1.  **Data Toolkit (`defi-data-toolkit`):** Uma biblioteca proprietária que coleta dados de múltiplas fontes (Binance, Deribit, The Graph, Blockchair, Alternative.me) e calcula indicadores técnicos avançados (RSI, SMA, F&G, Volatilidade Implícita).
2.  **Prediction Engine (IA):** Um modelo de Machine Learning (`scikit-learn`) treinado com dados históricos para prever a probabilidade de queda do mercado nos próximos 7 dias.
3.  **Estratégia Dinâmica:** Um motor de decisão que combina a previsão da IA com a análise técnica para definir o "Regime de Mercado":
    * **BEARISH (Medo):** Aciona estratégias de compra alavancada (AAVE Loop) e LPs de range largo.
    * **SIDEWAYS (Neutro):** Aciona estratégias de "Farming" com LPs de range apertado para coleta máxima de taxas.
    * **BULLISH (Euforia):** Sinaliza cautela ou realização de lucros.
4.  **Backtester V2:** Um motor de simulação robusto que valida a estratégia, calculando Impermanent Loss, taxas da Uniswap v3, juros de empréstimos e risco de liquidação (Health Factor).
5.  **Dashboard "Live":** Um painel interativo (Streamlit) que monitora as posições em tempo real.

## 📂 Estrutura do Projeto

* `backend/`: O núcleo do sistema (Python/FastAPI).
    * `src/prediction_engine.py`: Treinamento e inferência do modelo de ML.
    * `src/strategies.py`: Lógica financeira (AAVE Loop, Uniswap LPs).
    * `src/backtester.py`: Motor de simulação financeira.
* `frontend/`: Painel de controle (Streamlit) para visualização de dados e posições.
* `defi-data-toolkit/`: Biblioteca separada (submódulo) para coleta e processamento de dados.

## 🚀 Como Rodar (Instalação)

### Opção 1: Com Docker (Recomendado para Produção/Sócio)

O projeto está totalmente dockerizado para garantir paridade entre ambientes.

1.  **Clone o repositório (com submodules):**
    ```bash
    git clone --recurse-submodules [https://github.com/Kadats/defisys.git](https://github.com/Kadats/defisys.git)
    cd defisys
    ```

2.  **Inicie os serviços:**
    ```bash
    docker-compose up --build
    ```
    * O **Dashboard** estará acessível em: `http://localhost:3000`
    * A **API** estará acessível em: `http://localhost:8000`

### Opção 2: Desenvolvimento Local (Python + Poetry)

Para desenvolvedores que desejam alterar o código ou rodar backtests manuais.

**Pré-requisitos:** Python 3.12+ e Poetry instalados.

1.  **Instale as dependências:**
    ```bash
    cd defisys-strategy
    poetry install
    ```
    *(Nota: Se houver erros de dependência com a biblioteca local, certifique-se de que o `defi-data-toolkit` está atualizado e na pasta correta).*

2.  **Treine o Modelo e Rode o Backtest:**
    Este comando coleta dados novos, treina o modelo de IA do zero e executa a simulação histórica.
    ```bash
    make run
    ```
    *Os resultados serão salvos em `backtest_report.txt` e no banco de dados `crypto_data.db`.*

3.  **Rode o Dashboard Localmente:**
    ```bash
    # Terminal 1 (API)
    make run-api

    # Terminal 2 (Frontend)
    make run-frontend
    ```

## 🧪 Testes

A qualidade do código é garantida por uma suíte de testes unitários rigorosa.

```bash
poetry run pytest