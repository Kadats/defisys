# Em backend/src/api.py
from fastapi import FastAPI, HTTPException
from .system_runner import run_trading_system
import logging
import pandas as pd
import numpy as np
import math

logger = logging.getLogger(__name__)
app = FastAPI(title="DefiSys API")

@app.get("/api/v1/run_backtest")
def get_backtest_results():
    """
    Executa o sistema completo e retorna os resultados do backtest.
    """
    logger.info("Endpoint /api/v1/run_backtest chamado.")
    try:
        results = run_trading_system()
        df = results["full_dataframe"]

        # Limpeza: substitui inf/-inf e NaN por None para que o JSON seja válido
        df = df.replace([np.inf, -np.inf], None)
        df = df.where(pd.notnull(df), None)

        # Converte colunas datetime para string antes de serializar
        for col in df.select_dtypes(include=['datetime64[ns]']).columns:
            df[col] = df[col].astype(str)

        historical_data_json = df.to_dict(orient='records')

        # Sanitiza recursivamente objetos para JSON (substitui NaN/inf por None)
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(v) for v in obj]
            # numpy types: use pandas.isna to detect
            try:
                if pd.isna(obj):
                    return None
            except Exception:
                pass
            # numeric infinities
            if isinstance(obj, (float, int)):
                try:
                    if isinstance(obj, float) and not math.isfinite(obj):
                        return None
                except Exception:
                    pass
                return obj
            return obj

        safe_report = sanitize(results.get("backtest_report", {}))
        safe_historical = sanitize(historical_data_json)
        # decision_history is produced by the backtest and lives inside the backtest report
        safe_decision_history = sanitize(results.get('backtest_report', {}).get('decision_history', []))

        return {
            "report": safe_report,
            "historical_data": safe_historical,
            "decision_history": safe_decision_history
        }
    except Exception as e:
        logger.exception("Ocorreu um erro crítico ao executar o backtest via API.")
        # Levanta uma exceção HTTP para que o erro seja mais claro no lado do cliente
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {e}")