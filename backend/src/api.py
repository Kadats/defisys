from fastapi import FastAPI, HTTPException
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

# Imports internos
from backend.src.data.storage import get_data_from_db
from backend.src.data.pipeline import get_positions_from_db, get_predictions_from_db
from backend.src.system_runner import run_trading_system
from .config import DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_KLINES_LIMIT

logger = logging.getLogger(__name__)
app = FastAPI(title="DefiSys API")

# Cache simples em memória para não rodar backtest a cada F5
_SUMMARY_CACHE = {}

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

@app.get("/api/v1/summary")
def get_summary():
    """
    Retorna o Veredicto do Backtest. 
    Se o cache estiver vazio, roda o sistema.
    """
    global _SUMMARY_CACHE
    
    # Se já temos um resultado recente (ex: lógica de expiração poderia vir aqui), retorna ele
    if _SUMMARY_CACHE:
        return _SUMMARY_CACHE

    logger.info("Cache vazio. Rodando run_trading_system() para gerar resumo...")
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

@app.get("/api/v1/chart_data")
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


@app.get("/api/v1/backtest_period")
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


@app.get("/api/v1/positions")
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