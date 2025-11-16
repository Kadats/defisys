from fastapi import FastAPI, HTTPException
import logging
import pandas as pd
import numpy as np
import math
from .data_provider import get_data_from_db, get_positions_from_db, get_predictions_from_db
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
    Endpoint para buscar os dados de velas (OHLCV) E as predições de ML.
    """
    logger.info("Endpoint /api/v1/chart_data chamado.")
    try:
        klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines"
        
        # A variável deve ser 'df_klines' para bater com o resto da função
        df_klines = get_data_from_db(klines_table_name, DB_FILE, limit=365) 
        if df_klines.empty:
            logger.warning("Nenhum dado de klines encontrado no DB para o gráfico.")
            return {"error": "Nenhum dado de gráfico encontrado."}
        
            
        # Buscar e mesclar as predições
        df_predictions = get_predictions_from_db(DB_FILE)
        
        if not df_predictions.empty:
            # Mescla as predições com as velas
            df_final = pd.merge(df_klines, df_predictions, on='Open_time', how='left')
            # Preenche 'prediction' com 0 (neutro) e 'correct' com 0 (falso)
            df_final['prediction'] = df_final['prediction'].fillna(0).astype(int)
            df_final['prediction_correct'] = df_final['prediction_correct'].fillna(0).astype(int)
        else:
            logger.warning("Nenhuma predição de ML encontrada no DB. Retornando apenas klines.")
            df_final = df_klines
            df_final['prediction'] = 0
            df_final['prediction_correct'] = 0
            
        return sanitize_df_for_json(df_final)
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
            "closed_positions": sanitize_df_for_json(closed_df),
            "open_positions": sanitize_df_for_json(open_df),
            "closed_positions": sanitize_df_for_json(closed_df)
        }
    except Exception as e:
        logger.exception(f"Erro ao buscar positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        logger.exception(f"Erro ao buscar positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

