from fastapi import FastAPI, HTTPException
import logging
import pandas as pd
import numpy as np
import math
from .data_provider import get_data_from_db, get_positions_from_db
from .config import DB_FILE, DEFAULT_SYMBOL, DEFAULT_INTERVAL

logger = logging.getLogger(__name__)
app = FastAPI(title="DefiSys API")

# Helper para limpar dados para JSON
def sanitize_df_for_json(df: pd.DataFrame) -> list:
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)
    for col in df.select_dtypes(include=['datetime64[ns]']).columns:
        df[col] = df[col].astype(str)
    return df.to_dict(orient='records')

@app.get("/api/v1/chart_data")
def get_chart_data():
    """
    Endpoint para buscar os dados de velas (OHLCV) para o gráfico.
    Busca os últimos 365 dias por padrão.
    """
    logger.info("Endpoint /api/v1/chart_data chamado.")
    try:
        klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines"
        # Pega apenas os últimos 365 dias para o gráfico ficar rápido
        df = get_data_from_db(klines_table_name, DB_FILE, limit=365) 
        if df.empty:
            return {"error": "Nenhum dado de gráfico encontrado."}
            
        return sanitize_df_for_json(df)
    except Exception as e:
        logger.exception(f"Erro ao buscar chart_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/positions")
def get_positions():
    """
    Endpoint para buscar o log de posições (abertas e fechadas).
    """
    logger.info("Endpoint /api/v1/positions chamado.")
    try:
        df = get_positions_from_db(DB_FILE)
        if df.empty:
            return {"open_positions": [], "closed_positions": []}
            
        open_df = df[df['close_timestamp'].isnull()]
        closed_df = df[df['close_timestamp'].notnull()]
        
        return {
            "open_positions": sanitize_df_for_json(open_df),
            "closed_positions": sanitize_df_for_json(closed_df)
        }
    except Exception as e:
        logger.exception(f"Erro ao buscar positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

