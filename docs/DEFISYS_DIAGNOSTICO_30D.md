# DefiSys - Diagnostico de Janela 30 Dias

Data de referencia: 2026-02-25

## 1) Resumo de funcionamento (estado atual)

- Backend (Python/FastAPI) orquestra todo o fluxo de simulacao no container Docker: coleta de dados, treino ML walk-forward, backtest, persistencia em Postgres e exposicao via endpoints REST. O ponto central e a funcao `run_trading_system` em [backend/src/system_runner.py](../backend/src/system_runner.py).
- O ML walk-forward treina em historico completo e valida em janela posterior a `ML_TRAIN_SPLIT_DATE` (configuracao). A filtragem por dias (30 dias) acontece apos esse split, se `backtest_days` estiver definido. Veja [backend/src/system_runner.py](../backend/src/system_runner.py#L1-L245) e [backend/src/config.py](../backend/src/config.py#L1-L229).
- Os dados de mercado sao coletados para varios anos (DEFAULT_HISTORICAL_DAYS = 3200). O pipeline sempre busca e persiste o historico, e o filtro da janela acontece apenas no backtest. Veja [backend/src/data/pipeline.py](../backend/src/data/pipeline.py#L1-L240) e [backend/src/config.py](../backend/src/config.py#L1-L229).
- Frontend (Vue + Vite, nao Next.js) consome `/api/simulation` e `/api/simulation/run` para executar e exibir a simulacao. Veja [frontend/src/views/SimulationView.vue](../frontend/src/views/SimulationView.vue#L1-L401).

## 2) Analise de discrepancia de dados (janela 30 dias vs 2024)

### 2.1 Onde `start_date` e `end_date` sao definidos

- A API recebe `start_date`, `end_date` e `simulation_days` no payload de [backend/src/api.py](../backend/src/api.py#L28-L330). A chamada para `run_trading_system` repassa esses valores.
- No backend, `run_trading_system` aplica:
  1) split por `ML_TRAIN_SPLIT_DATE`.
  2) filtro por `backtest_days` (se informado).
  3) filtros de `start_date` e `end_date` (se informados).
  Veja [backend/src/system_runner.py](../backend/src/system_runner.py#L29-L170).

### 2.2 Limpeza de dados antigos (trades / token_metrics)

- A limpeza atual apaga apenas `positions_log` e `trades` via `clear_simulation_data`. Nao limpa `simulation_summary` nem `ml_predictions`. Veja [backend/src/data/storage.py](../backend/src/data/storage.py#L1018-L1041).
- Nao existe tabela `token_metrics` no codigo atual. As metricas de token ficam no `simulation_summary` (colunas `token_roi`, `alpha_vs_hold`, etc.). Veja [backend/src/data/storage.py](../backend/src/data/storage.py#L1038-L1140).
- Resultado: se a simulacao nova nao concluir (ou nao salvar summary), o frontend pode continuar exibindo o ultimo `simulation_summary` persistido, mesmo que antigo.

### 2.3 Logica de fetch de dados de mercado

- O pipeline coleta ate 3200 dias de historico (DEFAULT_HISTORICAL_DAYS), e isso e correto para treino. O filtro para 30 dias precisa ser aplicado apenas na etapa de backtest (dataframe `simulation_df`). Veja [backend/src/data/pipeline.py](../backend/src/data/pipeline.py#L1-L240) e [backend/src/system_runner.py](../backend/src/system_runner.py#L78-L160).
- O endpoint `/api/history` retorna TODO o historico de candles sem filtro. Se o grafico consumir esse endpoint, ele vai mostrar dados desde 2017/2024. Veja [backend/src/api.py](../backend/src/api.py#L74-L128).

## 3) Causa raiz provavel

Com base no codigo atual, a discrepancia de datas e mais consistente com:

1) **Janela de 30 dias nao aplicada quando `backtest_days` = 0**
   - `backtest_days` so limita a janela se for > 0. Caso o frontend nao envie `simulation_days` ou o endpoint usado para rodar a simulacao nao passe esse argumento, o backtest roda desde `ML_TRAIN_SPLIT_DATE` (2024-01-01). Veja [backend/src/system_runner.py](../backend/src/system_runner.py#L99-L152).
   - O Docker Compose nao define `GEMINI_BACKTEST_DAYS`, entao o fallback e 0. Veja [docker-compose.yml](../docker-compose.yml#L1-L45) e [backend/src/config.py](../backend/src/config.py#L90-L130).

2) **Persistencia de summary antigo**
   - `clear_simulation_data` nao limpa `simulation_summary`. O frontend usa `get_latest_simulation_summary()` como fonte principal. Se a simulacao atual falhar antes de salvar o summary, o frontend continua exibindo o summary anterior (que pode ser de 2024). Veja [backend/src/data/storage.py](../backend/src/data/storage.py#L1018-L1125) e [backend/src/api.py](../backend/src/api.py#L130-L220).

3) **Endpoints com historico completo**
   - O endpoint `/api/history` retorna candles de todo o banco, e pode ser usado em graficos sem qualquer filtro. Se o frontend estiver consumindo esse endpoint para o grafico principal, o range vai aparecer como 2024+. Veja [backend/src/api.py](../backend/src/api.py#L74-L128).

Nao ha evidencia de erro no SQL do frontend; ele apenas renderiza o que o backend entrega. Assim, o problema esta no backend (janela e/ou limpeza de summary) e possivelmente no modo como o backend e acionado (payload e fallback do Docker).

## 4) Plano de acao (alteracoes exatas de codigo)

### 4.1 Garantir janela rigorosa de 30 dias

**Ajuste 1: Forcar `backtest_days` > 0 quando nenhum valor for fornecido**

- Em [backend/src/system_runner.py](../backend/src/system_runner.py#L99-L152), substituir o fallback atual por um valor padrao consistente (30 dias) quando nao houver payload nem env.

```python
# Antes
# effective_days = backtest_days if backtest_days is not None else GEMINI_BACKTEST_DAYS

# Depois
effective_days = (
    backtest_days
    if backtest_days is not None
    else (GEMINI_BACKTEST_DAYS if GEMINI_BACKTEST_DAYS > 0 else 30)
)
```

**Ajuste 2: Persistir start/end do backtest no summary**

- Adicionar `backtest_start_date` e `backtest_end_date` no `simulation_summary` para auditoria e para o frontend exibir apenas a simulacao atual.
- Alterar schema em [backend/src/data/storage.py](../backend/src/data/storage.py#L1038-L1105) e o insert em [backend/src/data/storage.py](../backend/src/data/storage.py#L1107-L1185).
- Incluir os campos no `save_simulation_summary` em [backend/src/system_runner.py](../backend/src/system_runner.py#L165-L240).

Exemplo de alteracao (schema e insert):

```python
# storage.py - create_simulation_summary_table
cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS backtest_start_date TIMESTAMP")
cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS backtest_end_date TIMESTAMP")

# storage.py - save_simulation_summary insert
INSERT INTO simulation_summary (..., backtest_start_date, backtest_end_date)
VALUES (..., %s, %s)
```

**Ajuste 3: Forcar limite na coleta de candles do endpoint `/api/history`**

- Atualizar [backend/src/api.py](../backend/src/api.py#L74-L128) para filtrar por 30 dias (ou por `GEMINI_BACKTEST_DAYS`). Isso evita que o frontend mostre velas antigas no grafico.

```python
# Exemplo de filtro: usar max(open_time) - 30 dias
query = (
    "SELECT open_time AS time, open, high, low, close, volume "
    "FROM btcusdt_4h_klines "
    "WHERE open_time >= (SELECT MAX(open_time) - (30*24*60*60*1000) FROM btcusdt_4h_klines) "
    "ORDER BY open_time ASC"
)
```

### 4.2 Garantir que o frontend mostre apenas a simulacao atual

**Ajuste 4: Limpar `simulation_summary` e `ml_predictions` junto com trades**

- Atualizar `clear_simulation_data` em [backend/src/data/storage.py](../backend/src/data/storage.py#L1018-L1041) para apagar `simulation_summary` e `ml_predictions`, alem de `trades` e `positions_log`.
- Substituir `print()` por `logger.info()` (regra de logging do projeto).

```python
def clear_simulation_data() -> None:
    conn = create_connection()
    if not conn:
        logger.error("Nao foi possivel conectar ao banco para limpar dados")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM positions_log")
            cursor.execute("DELETE FROM trades")
            cursor.execute("DELETE FROM ml_predictions")
            cursor.execute("DELETE FROM simulation_summary")
        conn.commit()
        logger.info("Dados de simulacao anteriores limpos com sucesso.")
    except Exception as exc:
        logger.error("Erro ao limpar dados: %s", exc)
        conn.rollback()
    finally:
        conn.close()
```

**Ajuste 5 (opcional, mais robusto): versionar por `run_id`**

- Adicionar `run_id` (UUID) em `trades` e `simulation_summary` e sempre filtrar pelo ultimo `run_id` na API `/api/simulation`.
- Isso evita conflitos em simulacoes paralelas e elimina dependencia de `DELETE`.

### 4.3 Comandos de validacao (sempre via Docker Compose)

- Rodar simulacao com janela fixa (30 dias):
  - `docker compose exec backend python -m backend.src.system_runner`
- Verificar contagem de trades e datas:
  - `docker compose exec backend python -m backend.src.utils.analyze_proba`
  - (Opcional) adicionar um pequeno script de validacao que consulta `trades` e confirma o range de datas.

## 5) Conclusao

- O backend ja tem a logica para limitar a simulacao a 30 dias, mas ela depende de `backtest_days` > 0.
- A ausencia de `GEMINI_BACKTEST_DAYS` no Docker Compose e o uso de summaries antigos explicam o range desde 2024.
- As correcoes propostas centralizam a regra no backend, eliminam dados antigos e garantem que o frontend exiba somente a simulacao atual.
