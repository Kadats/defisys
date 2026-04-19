from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

# Imports internos
from backend.src.application import TradingWorkflowUseCases
from backend.src.ai import heuristics
from backend.src.data import storage
from backend.src.core.rpc_manager import RPCManager
from backend.src.data.storage import get_data_from_db, get_latest_simulation_summary
from backend.src.data.pipeline import get_positions_from_db, get_predictions_from_db, sync_market_data
from backend.src.interfaces.api import (
    paper_runtime_router,
    SandboxRunRequest,
    SimulationRunRequest,
    websocket_router,
)
from backend.src.system_runner import (
    run_trading_system as _run_trading_system,
    train_model_pipeline as _train_model_pipeline,
    run_simulation as _run_simulation,
)
from backend.src.services.analytics import get_simulation_results
from backend.src.utils.analytics import calculate_yearly_metrics
from backend.src.utils.log_handler import WebSocketHandler
from .config import (
    DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_KLINES_LIMIT, LOG_LEVEL,
    RPC_URL_PRIMARY, RPC_URL_SECONDARY, RPC_URL_DECENTRALIZED, NETWORK_TIMEOUT_SECONDS,
    PROJECT_ROOT
)
from .logging_config import setup_logging

# Initialize logging BEFORE creating the FastAPI app
setup_logging(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="DefiSys API")
app.include_router(websocket_router)
app.include_router(paper_runtime_router)

# RPC Manager Singleton para a API (Auditoria 2.1 e 3.2)
rpc_manager = RPCManager(
    primary_url=RPC_URL_PRIMARY,
    secondary_url=RPC_URL_SECONDARY,
    decentralized_url=RPC_URL_DECENTRALIZED,
    timeout=NETWORK_TIMEOUT_SECONDS
)

# Permite configuração dinâmica via variável de ambiente (IP público)
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Cache simples em memória para não rodar backtest a cada F5
_SUMMARY_CACHE = {}
_SIMULATION_RUNNING = False  # Flag para rastrear se simulação está em andamento

_use_cases = TradingWorkflowUseCases(
    train_model_fn=_train_model_pipeline,
    run_simulation_fn=_run_simulation,
    run_system_fn=_run_trading_system,
)


def train_model_pipeline():
    """Backward-compatible API-level alias for model training use case."""
    return _use_cases.train_model()


def run_simulation(
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = None,
    backtest_days: int | None = None,
    strategy_type: str = "accumulator",
    use_llm: bool = False,
):
    """Backward-compatible API-level alias for simulation use case."""
    return _use_cases.run_simulation(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        backtest_days=backtest_days,
        strategy_type=strategy_type,
        use_llm=use_llm,
    )


def run_trading_system():
    """Backward-compatible API-level alias for full system use case."""
    return _use_cases.run_trading_system()


def run_sandbox_simulation(payload: SandboxRunRequest):
    """Executa simulação isolada para o Sandbox Lab com Mock realista (Auditoria 3.3)"""
    import random
    from datetime import datetime, timedelta
    
    logger.info(f"Sandbox Lab: Iniciando simulação com AI Confidence {payload.ai_confidence}")
    
    # Simulação de processamento (delay fake)
    # Em produção isso seria assíncrono real, aqui retornamos direto para agilizar o lab
    
    # Gerar curva de equidade fake baseada no capital inicial
    current_equity = payload.initial_capital
    equity_curve = []
    start_date = datetime.now() - timedelta(days=30)
    
    # Tendência levemente alta se confidence for alto
    trend = (payload.ai_confidence - 0.5) * 0.02
    
    for i in range(30):
        # Volatilidade de 2%
        change = (random.random() - 0.5 + trend) * 0.02
        current_equity *= (1 + change)
        date_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        equity_curve.append({"date": date_str, "equity": round(current_equity, 2)})
    
    roi_total = ((current_equity / payload.initial_capital) - 1) * 100
    
    return {
        "success": True, 
        "job_id": f"sandbox-{int(datetime.now().timestamp())}",
        "metrics": {
            "roi_total": round(roi_total, 2),
            "max_drawdown": round(random.uniform(5.0, 15.0), 2),
            "win_rate": round(random.uniform(55.0, 75.0), 2)
        },
        "equity_curve": equity_curve
    }


@app.on_event("startup")
def setup_websocket_logging() -> None:
    root_logger = logging.getLogger()
    if any(isinstance(handler, WebSocketHandler) for handler in root_logger.handlers):
        return

    handler = WebSocketHandler()
    handler.setLevel(root_logger.level or logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    root_logger.addHandler(handler)


@app.on_event("startup")
async def startup_sync_market_data() -> None:
    """
    Sincroniza dados de mercado no startup do servidor.
    
    Esta função executa em background para não bloquear a inicialização do servidor.
    Coleta dados de:
    - Klines do Binance
    - Fear & Greed Index
    - Métricas On-chain
    - Funding Rate
    - Open Interest
    - Implied Volatility
    - Uniswap Pool Data
    """
    # Log direto para garantir que a função foi chamada
    print("="*80)
    print("🔄 STARTUP EVENT TRIGGERED - Iniciando sincronização de dados...")
    print("="*80)
    
    try:
        # Run in thread pool to avoid blocking server startup
        await run_in_threadpool(sync_market_data)
        print("="*80)
        print("✅ Sincronização concluída - API pronta para uso")
        print("="*80)
    except Exception as e:
        print(f"❌ ERRO na sincronização: {e}")
        logger.error(f"Erro durante sincronização de dados no startup: {e}", exc_info=True)
        logger.warning("Servidor iniciado, mas sincronização de dados falhou. Execute manualmente se necessário.")


def sanitize_for_json(obj):
    """Converte Decimals e NaNs para formatos aceitos em JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    return obj

def sanitize_df_for_json(df: pd.DataFrame) -> list:
    """Helper para DataFrames"""
    # Substitui NaNs/Infs
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)
    
    # Converte para dict
    records = df.to_dict(orient='records')
    # Sanitiza recursivamente (para pegar Decimals dentro das linhas)
    return sanitize_for_json(records)


@app.get(
    "/api/history",
    tags=["Market Data"],
    summary="Get Klines History",
    description="Returns OHLCV candles for charting from btcusdt_4h_klines."
)
def get_history():
    conn = None
    try:
        conn = storage.create_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")

        query = (
            "SELECT open_time AS time, open, high, low, close, volume "
            "FROM btcusdt_4h_klines ORDER BY open_time ASC"
        )
        df = pd.read_sql(query, conn)
        if df.empty:
            return []

        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return sanitize_for_json(df.to_dict(orient="records"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao buscar history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@app.get("/api/system/health", tags=["Control Center"])
async def get_system_health():
    """Retorna o estado de saúde dos 3 RPCs (Nível 3.2)"""
    return rpc_manager.get_all_health()


@app.get("/api/system/logs", tags=["Control Center"])
def get_system_logs():
    """Retorna as últimas 50 linhas do arquivo de log persistente (Auditoria 3.3)"""
    log_file = os.path.join(PROJECT_ROOT, 'backend', 'logs', 'defisys.log')
    
    if not os.path.exists(log_file):
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # Para arquivos grandes, o ideal seria ler do fim, 
            # mas para 50 linhas o readlines() [-50:] é seguro no MVP
            lines = f.readlines()
            return [line.strip() for line in lines[-50:]]
    except Exception as e:
        logger.error(f"Erro ao ler arquivo de log: {e}")
        return [f"Erro ao recuperar logs: {e}"]


@app.get("/api/system/indicators", tags=["Control Center"])
def get_indicators():
    """Retorna indicadores críticos em tempo real"""
    klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines".lower()
    df = get_data_from_db(klines_table_name, limit=100)
    if df.empty:
        return {"rsi": 0, "fear_and_greed": 0, "market_regime": "unknown"}
    return heuristics.get_market_indicators(df)


@app.post("/api/sandbox/run", tags=["Control Center"])
async def post_sandbox_run(payload: SandboxRunRequest):
    """Dispara uma simulação no Sandbox Lab"""
    result = await run_in_threadpool(run_sandbox_simulation, payload)
    return result


@app.get(
    "/api/simulation",
    tags=["Simulation"],
    summary="Get Simulation Results",
    description="Returns simulation KPIs, official summary, and trade history."
)
def get_simulation():
    try:
        # Get the simulation results (trades from DB)
        results = get_simulation_results()
        
        # Garantir que trades estão ordenados por timestamp DESC (mais recentes primeiro)
        if results.get('trades'):
            results['trades'] = sorted(results['trades'], key=lambda x: x.get('date', ''), reverse=True)
        
        # Get the OFFICIAL summary from the database (the "truth")
        official_summary = get_latest_simulation_summary()
        
        # If we have official summary, use it; otherwise use calculated values
        if official_summary:
            kpis = {
                "total_trades": official_summary.get('total_trades', results['kpis']['total_trades']),
                "initial_balance": official_summary.get('initial_capital', results['kpis']['initial_balance']),
                "final_balance": official_summary.get('total_equity', results['kpis']['final_balance']),
                "roi": official_summary.get('roi_percent', results['kpis']['roi']),
                "benchmark_roi": official_summary.get('benchmark_roi_percent', results['kpis']['benchmark_roi']),
            }
            
            # Estruturar summary com as chaves esperadas pelo frontend
            summary = {
                "total_trades": official_summary.get('total_trades'),
                "initial_capital": official_summary.get('initial_capital'),
                "total_equity": official_summary.get('total_equity'),
                "roi_percent": official_summary.get('roi_percent'),
                "benchmark_roi_percent": official_summary.get('benchmark_roi_percent'),
                # Tesourarias Isoladas
                "wallet_spot_usd": official_summary.get('cash_balance'),
                "wallet_spot_btc": official_summary.get('btc_amount'),
                "wallet_spot_total_usd": (official_summary.get('cash_balance', 0) + 
                                         (official_summary.get('btc_amount', 0) * official_summary.get('btc_price_final', 0))),
                "wallet_lp_value_usd": official_summary.get('wallet_lp_value_usd'),
                "lp_active_count": official_summary.get('lp_active_count'),
                "lp_fees_usd": official_summary.get('lp_fees_usd'),
                "aave_collateral_usd": official_summary.get('aave_collateral_usd'),
                "aave_debt_usd": official_summary.get('aave_debt_usd'),
                "aave_health_factor": official_summary.get('aave_health_factor'),
                # Token metrics
                "alpha_vs_hold": official_summary.get('alpha_vs_hold'),
                "initial_token_balance": official_summary.get('initial_token_balance'),
                "final_token_balance": official_summary.get('final_token_balance'),
                "token_roi": official_summary.get('token_roi'),
            }
        else:
            # Fallback: Calculate summary from computed KPIs (trades already have post_trade_equity)
            logger.info("✓ No official summary in DB, using calculated KPIs for summary")
            kpis = results['kpis']
            
            # Calcular valores das tesourarias a partir do último trade
            last_equity = results['kpis']['final_balance']
            summary = {
                "total_trades": results['kpis']['total_trades'],
                "initial_capital": results['kpis']['initial_balance'],
                "total_equity": last_equity,
                "roi_percent": results['kpis']['roi'],
                "benchmark_roi_percent": results['kpis']['benchmark_roi'],
                # Tesourarias Isoladas - valores padrões (0) se não houver summary
                "wallet_spot_usd": 0,
                "wallet_spot_btc": 0,
                "wallet_spot_total_usd": 0,
                "wallet_lp_value_usd": 0,
                "lp_active_count": 0,
                "lp_fees_usd": 0,
                "aave_collateral_usd": 0,
                "aave_debt_usd": 0,
                "aave_health_factor": 0,
                # Token metrics
                "alpha_vs_hold": 0,
                "initial_token_balance": 0,
                "final_token_balance": 0,
                "token_roi": 0,
            }
        
        response = {
            "kpis": kpis,
            "trades": results['trades'],
            "summary": summary  # ALWAYS return summary object (never null)
        }
        
        return sanitize_for_json(response)
    except Exception as e:
        logger.exception("Erro ao buscar simulation results: %s", e)
        # Retornar resposta vazia válida em vez de erro 500
        return {
            "kpis": {
                "total_trades": 0,
                "initial_balance": 1000.0,
                "final_balance": 1000.0,
                "roi": 0.0,
                "benchmark_roi": 0.0,
            },
            "trades": [],
            "summary": {
                "total_trades": 0,
                "initial_capital": 1000.0,
                "total_equity": 1000.0,
                "roi_percent": 0.0,
                "benchmark_roi_percent": 0.0,
                "wallet_spot_usd": 0.0,
                "wallet_spot_btc": 0.0,
                "wallet_spot_total_usd": 0.0,
                "wallet_lp_value_usd": 0.0,
                "lp_active_count": 0,
                "lp_fees_usd": 0.0,
                "aave_collateral_usd": 0.0,
                "aave_debt_usd": 0.0,
                "aave_health_factor": 0.0,
                "alpha_vs_hold": 0.0,
                "initial_token_balance": 0.0,
                "final_token_balance": 0.0,
                "token_roi": 0.0,
            }
        }


@app.post(
    "/api/model/train",
    tags=["Model"],
    summary="Train ML Model",
    description="Trains the XGBoost prediction model using historical data. Must be run before simulation."
)
async def train_model():
    """
    Fase 2: Treina o modelo de Machine Learning.
    
    Este endpoint:
    - Carrega dados históricos do banco de dados
    - Faz split temporal Walk-Forward (treino até 2023-12-31)
    - Treina o modelo XGBClassifier
    - Gera predições para todo o histórico
    - Salva predições no banco de dados
    
    Retorna:
        dict: Relatório do treinamento com métricas e número de predições geradas
    """
    logger.info("🤖 Endpoint /api/model/train chamado - iniciando treino do modelo...")
    
    def train_and_return():
        try:
            result = train_model_pipeline()
            logger.info("✓ Treinamento de ML concluído!")
            return result
        except Exception as e:
            logger.exception(f"❌ Erro no treinamento: {e}")
            return {
                "success": False,
                "error": str(e),
                "predictions_generated": 0
            }
    
    result = await run_in_threadpool(train_and_return)
    
    if result.get("success"):
        return {
            "status": "completed",
            "message": f"Modelo treinado com sucesso! {result['predictions_generated']} predições geradas.",
            "data": result
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Falha no treinamento do modelo: {result.get('error', 'Unknown error')}"
        )


@app.post(
    "/api/simulation/run",
    tags=["Simulation"],
    summary="Run Simulation",
    description="Triggers the trading system to run without blocking the API."
)
async def run_simulation_endpoint(payload: SimulationRunRequest):
    """
    Fase 3-4: Executa a simulação de trading.
    
    Este endpoint:
    - Valida que o modelo foi treinado (verifica existência de predições)
    - Carrega predições de ML do banco
    - Executa o TradingEngine com a estratégia escolhida
    - Salva trades, positions e summary no banco
    
    IMPORTANTE: Execute /api/model/train antes de usar este endpoint!
    
    Args:
        payload: Parâmetros da simulação (datas, capital inicial, dias)
    
    Retorna:
        dict: Status da simulação iniciada em background
    """
    global _SUMMARY_CACHE, _SIMULATION_RUNNING
    
    # VALIDAÇÃO: Verificar se há predições no banco de dados
    logger.info("🔍 Validando existência de predições no banco de dados...")
    predictions_df = get_predictions_from_db()
    
    if predictions_df is None or predictions_df.empty:
        logger.error("❌ Nenhuma predição encontrada no banco de dados!")
        raise HTTPException(
            status_code=400,
            detail="Modelo não treinado. Por favor, execute o treinamento antes de simular."
        )
    
    logger.info(f"✓ Validação OK: {len(predictions_df):,} predições encontradas no banco")
    
    # 🧹 LIMPAR CACHE ANTIGO - força recompute dos resultados
    _SUMMARY_CACHE = {}
    _SIMULATION_RUNNING = True
    logger.info("✓ Cache limpo e flag iniciado. Disparando simulação...")
    
    def run_and_mark_done():
        try:
            run_simulation(
                payload.start_date,
                payload.end_date,
                payload.initial_capital,
                backtest_days=payload.simulation_days,
                strategy_type=payload.strategy_type,
                use_llm=payload.use_llm,
            )
            logger.info("✓ Simulação concluída!")
        except Exception as e:
            logger.exception(f"❌ Erro na simulação: {e}")
        finally:
            global _SIMULATION_RUNNING
            _SIMULATION_RUNNING = False
    
    asyncio.create_task(
        run_in_threadpool(run_and_mark_done)
    )
    return {
        "status": "started",
        "message": "Simulação iniciada em background. Aguarde alguns segundos para ver os resultados."
    }

@app.get(
    "/api/simulation/status",
    tags=["Simulation"],
    summary="Get Simulation Status",
    description="Returns whether simulation is currently running."
)
def get_simulation_status():
    """
    Retorna o status atual da simulação (rodando ou parada).
    Útil para polling no frontend.
    """
    try:
        # Obter summary oficial do banco
        official_summary = get_latest_simulation_summary()
        
        return {
            "running": _SIMULATION_RUNNING,
            "has_results": official_summary is not None,
            "trades_count": official_summary.get('total_trades', 0) if official_summary else 0
        }
    except Exception as e:
        logger.exception("Erro ao buscar status: %s", e)
        return {
            "running": _SIMULATION_RUNNING,
            "has_results": False,
            "trades_count": 0,
            "error": str(e)
        }

@app.get(
    "/api/simulation/summary",
    tags=["Simulation"],
    summary="Get Isolated Treasuries Summary",
    description="Returns the final state of 3 distinct wallets: Spot (USD/BTC), DeFi (LPs), and AAVE (Collateral/Debt)."
)
def get_treasuries_summary():
    """
    Retorna o estado final de 3 carteiras isoladas (Tesourarias):
    
    1. 🏦 SPOT: USD em caixa + BTC em HODL
    2. 🌾 DeFi: Capital alocado em Uniswap LPs
    3. 👻 AAVE: BTC em garantia (collateral), Dívida (borrow), Health Factor
    """
    try:
        # Obter o último summary oficial do banco
        official_summary = get_latest_simulation_summary()
        
        if official_summary:
            logger.info("✓ Returning treasuries summary from database")
            
            # Estruturar resposta com 3 carteiras isoladas
            response = {
                "spot": {
                    "label": "🏦 Bot Wallet (Spot)",
                    "usd_available": official_summary.get("cash_balance", 0),
                    "btc_balance": official_summary.get("btc_amount", 0),
                    "btc_price": official_summary.get("btc_price_final", 0),
                    "total_usd": (official_summary.get("cash_balance", 0) + 
                                 (official_summary.get("btc_amount", 0) * official_summary.get("btc_price_final", 0)))
                },
                "defi": {
                    "label": "🌾 DeFi LPs (Yield)",
                    "capital_allocated": official_summary.get("wallet_lp_value_usd", 0),
                    "active_positions": official_summary.get("lp_active_count", 0),
                    "fees_earned": official_summary.get("lp_fees_usd", 0),
                },
                "aave": {
                    "label": "👻 AAVE (Crédito)",
                    "collateral_btc_usd": official_summary.get("aave_collateral_usd", 0),
                    "debt_borrow_usd": official_summary.get("aave_debt_usd", 0),
                    "health_factor": official_summary.get("aave_health_factor", 0),
                    "health_status": _get_health_factor_status(official_summary.get("aave_health_factor", 0))
                },
                "summary": {
                    "initial_capital": official_summary.get("initial_capital", 0),
                    "total_equity": official_summary.get("total_equity", 0),
                    "roi_percent": official_summary.get("roi_percent", 0),
                    "benchmark_roi_percent": official_summary.get("benchmark_roi_percent", 0)
                }
            }
            
            return sanitize_for_json(response)
        else:
            logger.warning("No simulation summary found. Run simulation first.")
            # Retornar valores padrão em vez de erro
            return {
                "spot": {"label": "🏦 Bot Wallet (Spot)", "usd_available": 0, "btc_balance": 0, "btc_price": 0, "total_usd": 0},
                "defi": {"label": "🌾 DeFi LPs (Yield)", "capital_allocated": 0, "active_positions": 0, "fees_earned": 0},
                "aave": {"label": "👻 AAVE (Crédito)", "collateral_btc_usd": 0, "debt_borrow_usd": 0, "health_factor": 0, "health_status": "NONE"},
                "summary": {"initial_capital": 0, "total_equity": 0, "roi_percent": 0, "benchmark_roi_percent": 0}
            }
    
    except Exception as e:
        logger.exception("Erro ao buscar treasuries summary: %s", e)
        # Retornar valores padrão em vez de erro 500
        return {
            "spot": {"label": "🏦 Bot Wallet (Spot)", "usd_available": 0, "btc_balance": 0, "btc_price": 0, "total_usd": 0},
            "defi": {"label": "🌾 DeFi LPs (Yield)", "capital_allocated": 0, "active_positions": 0, "fees_earned": 0},
            "aave": {"label": "👻 AAVE (Crédito)", "collateral_btc_usd": 0, "debt_borrow_usd": 0, "health_factor": 0, "health_status": "NONE"},
            "summary": {"initial_capital": 0, "total_equity": 0, "roi_percent": 0, "benchmark_roi_percent": 0}
        }

def _get_health_factor_status(health_factor: float) -> str:
    """
    Retorna status de saúde do AAVE baseado no health factor.
    Verde: > 1.5
    Amarelo: 1.2 - 1.5
    Vermelho: < 1.2
    """
    if health_factor >= 1.5:
        return "SAFE"  # Verde
    elif health_factor >= 1.2:
        return "WARNING"  # Amarelo
    elif health_factor > 0:
        return "DANGER"  # Vermelho
    else:
        return "LIQUIDATED"  # Preto (liquidação)

@app.get(
    "/api/v1/summary",
    tags=["Dashboard"],
    summary="Get Backtest Summary",
    description="Returns the official backtest summary from database, including strategy returns, BTC HODL benchmark, ML accuracy, and win rate."
)
def get_summary():
    """
    Retorna o Veredicto do Backtest. 
    Primeiro tenta obter o OFFICIAL do banco de dados (simulation_summary).
    Se não existir, roda o sistema para gerar um novo.
    """
    global _SUMMARY_CACHE
    
    # Primeiramente, tenta obter o summary OFFICIAL do banco de dados
    official_summary = get_latest_simulation_summary()
    if official_summary:
        logger.info("✓ Using OFFICIAL summary from database")
        
        # Calcula apenas as métricas adicionais que não estão em simulation_summary
        positions_df = get_positions_from_db(include_open=False, include_closed=True)
        win_rate = 0.0
        if not positions_df.empty:
            wins = positions_df[positions_df['final_profit_usd'] > 0]
            win_rate = len(wins) / len(positions_df)
        
        preds_df = get_predictions_from_db()
        accuracy = 0.0
        current_action = "AGUARDAR"
        
        if not preds_df.empty and 'prediction_correct' in preds_df.columns:
            try:
                preds_df['prediction_correct'] = pd.to_numeric(preds_df['prediction_correct'], errors='coerce')
            except Exception as e:
                logger.warning(f"Error converting prediction_correct to numeric: {e}")
            valid_predictions = preds_df['prediction_correct'].dropna()
            if len(valid_predictions) > 0:
                accuracy = float(valid_predictions.astype(float).mean())
            
            if 'prediction' in preds_df.columns and len(preds_df) > 0:
                last_pred = preds_df.iloc[-1]['prediction']
                if last_pred == 1:
                    current_action = "COMPRAR"
                elif last_pred == 0:
                    current_action = "AGUARDAR"
        
        summary_data = {
            "initial_capital": official_summary.get("initial_capital", 0),
            "final_capital": official_summary.get("total_equity", 0),
            "net_profit": official_summary.get("total_equity", 0) - official_summary.get("initial_capital", 0),
            "strategy_return_pct": official_summary.get("roi_percent", 0),
            "btc_hodl_return_pct": official_summary.get("benchmark_roi_percent", 0),
            "win_rate": win_rate,
            "ml_accuracy": accuracy,
            "current_action": current_action,
            "backtest_start_date": None,  # Could be added to simulation_summary if needed
            "backtest_end_date": None,    # Could be added to simulation_summary if needed
            "last_updated": official_summary.get("timestamp", datetime.now().isoformat())
        }
        
        _SUMMARY_CACHE = sanitize_for_json(summary_data)
        return _SUMMARY_CACHE
    
    # Se não temos summary OFFICIAL, rodamos o sistema
    logger.info("No official summary found. Running run_trading_system() to generate one...")
    if _SUMMARY_CACHE:
        return _SUMMARY_CACHE

    try:
        # Executa o sistema completo
        result = run_trading_system()
        report = result.get("backtest_report", {})
        
        # Se deu erro no backtest
        if "error" in report:
             raise HTTPException(status_code=500, detail=report["error"])

        # Calcula métricas adicionais
        positions_df = get_positions_from_db(include_open=False, include_closed=True)
        win_rate = 0.0
        if not positions_df.empty:
            wins = positions_df[positions_df['final_profit_usd'] > 0]
            win_rate = len(wins) / len(positions_df)

        preds_df = get_predictions_from_db()
        accuracy = 0.0  # Default to 0.0
        current_action = "AGUARDAR"
        
        if not preds_df.empty and 'prediction_correct' in preds_df.columns:
            # Convert to numeric, coerce errors to NaN, then drop for accuracy calc
            try:
                preds_df['prediction_correct'] = pd.to_numeric(preds_df['prediction_correct'], errors='coerce')
            except Exception as e:
                logger.warning(f"Error converting prediction_correct to numeric: {e}")
            valid_predictions = preds_df['prediction_correct'].dropna()
            logger.info(f"ML Accuracy: {len(valid_predictions)} valid rows of {len(preds_df)} total for calculation")
            
            if len(valid_predictions) > 0:
                # Convert to float and calculate mean
                accuracy = float(valid_predictions.astype(float).mean())
                logger.info(f"ML Accuracy calculated: {accuracy*100:.2f}% from {len(valid_predictions)} valid predictions")
            else:
                # Explicitly return 0.0 if no valid predictions
                accuracy = 0.0
                logger.warning("No valid predictions found in database - returning 0.0 for accuracy")
            
            # Get latest prediction for current action
            if 'prediction' in preds_df.columns and len(preds_df) > 0:
                last_pred = preds_df.iloc[-1]['prediction']
                if last_pred == 1:
                    current_action = "COMPRAR"
                elif last_pred == 0:
                    current_action = "AGUARDAR"
        else:
            logger.warning("Predictions DataFrame is empty or missing 'prediction_correct' column")
        
        # Extract backtest period from report
        backtest_start_date = report.get("start_date", None)
        backtest_end_date = report.get("end_date", None)
        
        # Monta o objeto de resposta
        summary_data = {
            "initial_capital": report.get("initial_capital_usd", 0),
            "final_capital": report.get("final_usd_value", 0),
            "net_profit": report.get("profit_usd", 0),
            "strategy_return_pct": report.get("profit_percentage_usd", 0),
            "btc_hodl_return_pct": report.get("btc_benchmark_profit_percentage", 0),
            "win_rate": win_rate,
            "ml_accuracy": accuracy,
            "current_action": current_action,
            "backtest_start_date": backtest_start_date,
            "backtest_end_date": backtest_end_date,
            "last_updated": datetime.now().isoformat()
        }
        
        # Salva no cache e sanitiza
        _SUMMARY_CACHE = sanitize_for_json(summary_data)
        return _SUMMARY_CACHE

    except Exception as e:
        logger.exception("Erro crítico ao gerar resumo: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/trade_history",
    tags=["Dashboard"],
    summary="Get Transaction Log",
    description="Returns the detailed transaction log of all trades, harvests, and rebalancing actions from the backtest."
)
def get_trade_history():
    """
    V13: Retorna o Diário de Bordo (Transaction Log) do backtest.
    Inclui todos os movimentos: BUY_HODL, OPEN_LP, CLOSE_LP, HARVEST, DEBT_REPAY, etc.
    """
    global _SUMMARY_CACHE
    
    logger.info("Fetching trade history from backtest results...")
    try:
        # Se não temos cache, rodamos o sistema
        if not _SUMMARY_CACHE:
            logger.info("Cache vazio. Rodando run_trading_system() para gerar histórico...")
            result = run_trading_system()
            report = result.get("backtest_report", {})
            
            if "error" in report:
                raise HTTPException(status_code=500, detail=report["error"])
            
            # Store in cache
            positions_df = get_positions_from_db(include_open=False, include_closed=True)
            win_rate = 0.0
            if not positions_df.empty:
                wins = positions_df[positions_df['final_profit_usd'] > 0]
                win_rate = len(wins) / len(positions_df)

            preds_df = get_predictions_from_db()
            accuracy = 0.0
            
            if not preds_df.empty and 'prediction_correct' in preds_df.columns:
                try:
                    preds_df['prediction_correct'] = pd.to_numeric(preds_df['prediction_correct'], errors='coerce')
                except Exception as e:
                    logger.warning(f"Error converting prediction_correct to numeric: {e}")
                valid_predictions = preds_df['prediction_correct'].dropna()
                if len(valid_predictions) > 0:
                    accuracy = float(valid_predictions.astype(float).mean())
            
            backtest_start_date = report.get("start_date", None)
            backtest_end_date = report.get("end_date", None)
            
            summary_data = {
                "initial_capital": report.get("initial_capital_usd", 0),
                "final_capital": report.get("final_usd_value", 0),
                "net_profit": report.get("profit_usd", 0),
                "strategy_return_pct": report.get("profit_percentage_usd", 0),
                "btc_hodl_return_pct": report.get("btc_benchmark_profit_percentage", 0),
                "win_rate": win_rate,
                "ml_accuracy": accuracy,
                "current_action": "AGUARDAR",
                "backtest_start_date": backtest_start_date,
                "backtest_end_date": backtest_end_date,
                "last_updated": datetime.now().isoformat()
            }
            
            _SUMMARY_CACHE = sanitize_for_json(summary_data)
        else:
            report = _SUMMARY_CACHE  # Use cached report
        
        # Extract transaction_log from the backtest result
        # Run again to get fresh transaction log (since cache only stores summary)
        result = run_trading_system()
        backtest_result = result.get("backtest_report", {})
        transaction_log = backtest_result.get("transaction_log", [])
        
        # V13: Convert transaction_log to JSON-serializable format
        transaction_history = []
        for trans in transaction_log:
            # Convert timestamp to ISO string
            timestamp = trans.get("timestamp")
            if isinstance(timestamp, pd.Timestamp):
                timestamp_str = timestamp.isoformat()
            elif hasattr(timestamp, 'isoformat'):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp)
            
            # Build transaction record
            transaction_history.append({
                "timestamp": timestamp_str,
                "action": trans.get("action", ""),
                "btc_price": float(trans.get("btc_price", 0)),
                "usd_amount": float(trans.get("usd_amount", 0)),
                "btc_amount": float(trans.get("btc_amount", 0)),
                "fee_usd": float(trans.get("fee_usd", 0)),
                "pnl_usd": float(trans.get("pnl_usd", 0)),
                "details": trans.get("details", "")
            })
        
        # Calculate total gas paid
        total_gas_paid = sum(t.get("fee_usd", 0) for t in transaction_history)
        
        return {
            "transactions": sanitize_for_json(transaction_history),
            "total_gas_paid": total_gas_paid,
            "total_transactions": len(transaction_history)
        }
        
    except Exception as e:
        logger.exception("Erro ao buscar transaction history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/chart_data",
    tags=["Market Data"],
    summary="Get Klines (OHLCV Data)",
    description="Returns historical candlestick data (Open, High, Low, Close, Volume) for charting. Supports optional date filtering via 'start' and 'end' parameters. Default limit is 1000 candles."
)
def get_chart_data(start: str = None, end: str = None):
    """
    Retorna dados de velas (klines) para o gráfico.
    
    Parâmetros opcionais:
    - start: Data inicial em formato ISO (YYYY-MM-DD) ou timestamp
    - end: Data final em formato ISO (YYYY-MM-DD) ou timestamp
    
    Se não informados, retorna todo o histórico disponível.
    """
    try:
        klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines".lower()

        # FIX: Use DEFAULT_KLINES_LIMIT instead of hardcoded 365 to show full backtest period
        df_klines = get_data_from_db(klines_table_name, limit=DEFAULT_KLINES_LIMIT)
        
        if df_klines.empty:
            return []
        
        # Apply optional date filtering
        if start is not None or end is not None:
            try:
                if 'Open_time' in df_klines.columns:
                    df_klines['Open_time'] = pd.to_datetime(df_klines['Open_time'])
                    
                    if start is not None:
                        start_date = pd.to_datetime(start)
                        df_klines = df_klines[df_klines['Open_time'] >= start_date]
                        logger.info(f"Filtered chart data from {start_date}")
                    
                    if end is not None:
                        end_date = pd.to_datetime(end)
                        df_klines = df_klines[df_klines['Open_time'] <= end_date]
                        logger.info(f"Filtered chart data to {end_date}")
            except Exception as e:
                logger.warning(f"Error filtering chart data by dates: {e}. Returning unfiltered data.")
        
        return sanitize_df_for_json(df_klines)
    except Exception as e:
        logger.exception(f"Erro ao buscar chart_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/backtest_period",
    tags=["Dashboard"],
    summary="Get Backtest Period",
    description="Returns the start and end dates of the most recent backtest execution. Useful for syncing frontend chart zoom with backtest window."
)
def get_backtest_period():
    """
    Retorna o período de datas do último backtest executado.
    Útil para sincronizar o gráfico com o período testado.
    """
    try:
        # Se temos cache de summary, extrair as datas
        if _SUMMARY_CACHE:
            return {
                "start_date": _SUMMARY_CACHE.get("backtest_start_date"),
                "end_date": _SUMMARY_CACHE.get("backtest_end_date")
            }
        
        # Caso contrário, executar um resumo rápido
        result = run_trading_system()
        report = result.get("backtest_report", {})
        
        return {
            "start_date": report.get("start_date"),
            "end_date": report.get("end_date")
        }
    except Exception as e:
        logger.exception(f"Erro ao buscar backtest_period: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/market_analysis",
    tags=["Market Data"],
    summary="Get Market X-Ray",
    description="Returns volatility metrics and analysis grouped by year. Includes total return, max drawdown, explosive days (>5%), severe dumps (<-5%), and daily return distribution. Essential for understanding market behavior patterns."
)
def get_market_analysis():
    """
    Returns yearly market metrics: returns, drawdowns, explosive days, etc.
    Analyzes ALL historical klines to provide year-by-year insights.
    """
    try:
        klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines".lower()
        # Fetch ALL klines without limit for complete historical analysis
        df_klines = get_data_from_db(klines_table_name, limit=None)
        
        if df_klines.empty:
            logger.warning("No klines data available for market analysis.")
            return {}
        
        logger.info(f"Analyzing {len(df_klines)} klines for yearly metrics...")
        # Calculate yearly metrics
        yearly_metrics = calculate_yearly_metrics(df_klines)
        
        # FIX: Convert integer keys to strings for valid JSON serialization
        metrics_str_keys = {str(k): v for k, v in yearly_metrics.items()}
        logger.info(f"Market analysis computed for {len(metrics_str_keys)} years.")
        
        # Sanitize for JSON
        return sanitize_for_json(metrics_str_keys)
    except Exception as e:
        logger.exception(f"Erro ao analisar mercado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/positions",
    tags=["Execution"],
    summary="Get Trading Positions",
    description="Returns open and closed trading positions with profit/loss details. Used to track position history and validate strategy execution."
)
def get_positions():
    try:
        df = get_positions_from_db()
        if df.empty:
            return {"open_positions": [], "closed_positions": []}
            
        open_df = df[df['close_timestamp'].isnull()]
        closed_df = df[df['close_timestamp'].notnull()]
        
        return {
            "open_positions": sanitize_df_for_json(open_df),
            "closed_positions": sanitize_df_for_json(closed_df)
        }
    except Exception as e:
        logger.exception(f"Erro positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
