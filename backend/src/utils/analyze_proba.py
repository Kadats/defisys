import pandas as pd
import logging
from sqlalchemy import create_engine, text
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("PROBA_ANALYSIS")

def get_db_connection():
    # Ajuste para conectar no localhost se estiver rodando de fora, 
    # ou use as variaveis de ambiente se estiver dentro do container
    db_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://defisys_user:defisys_pass@db:5432/defisys_db'
    )
    return create_engine(db_url)

def analyze():
    engine = get_db_connection()
    logger.info("--- 📊 ANÁLISE DE PROBABILIDADES (XGBoost) ---")
    
    try:
        with engine.connect() as conn:
            # 1. Descobrir nomes das colunas primeiro
            # Trazemos 0 linhas apenas para ler o cabeçalho
            df_head = pd.read_sql("SELECT * FROM ml_predictions LIMIT 0", conn)
            cols = df_head.columns.tolist()
            logger.info(f"Colunas encontradas: {cols}")

            # 2. Identificar coluna de Tempo
            time_col = next((c for c in ['open_time', 'timestamp', 'date', 'time'] if c in cols), None)
            if not time_col:
                logger.error("❌ Não encontrei coluna de tempo (open_time, timestamp, date).")
                return

            # 3. Identificar coluna de Probabilidade
            proba_col = next((c for c in ['prediction_proba', 'prob', 'proba', 'probability'] if c in cols), None)
            if not proba_col:
                logger.error("❌ Não encontrei coluna de probabilidade.")
                return

            # 4. Fazer a Query Real
            logger.info(f"Usando coluna de tempo: '{time_col}' e probabilidade: '{proba_col}'")
            query = f"SELECT * FROM ml_predictions ORDER BY {time_col} ASC"
            df = pd.read_sql(query, conn)
            
            if df.empty:
                logger.warning("⚠️ Tabela vazia. Rode a simulação para gerar dados.")
                return

            # 5. Análise
            total = len(df)
            bull_signals = df[df['prediction'] == 1]
            
            logger.info(f"\nTotal de Candles: {total}")
            logger.info(f"Sinais de COMPRA (Classe 1): {len(bull_signals)}")
            
            if bull_signals.empty:
                logger.warning("Modelo nunca previu compra.")
                return

            probas = bull_signals[proba_col]
            
            logger.info(f"\n--- Estatísticas de Confiança (Quando diz Compra) ---")
            logger.info(f"Média: {probas.mean():.4f}")
            logger.info(f"Máx:   {probas.max():.4f}")
            logger.info(f"50% dos sinais são menores que: {probas.quantile(0.50):.4f}")
            logger.info(f"75% dos sinais são menores que: {probas.quantile(0.75):.4f}")
            logger.info(f"90% dos sinais são menores que: {probas.quantile(0.90):.4f}")

            logger.info("\n--- 🎯 Se mudássemos o Threshold... ---")
            for th in [0.50, 0.55, 0.60, 0.65, 0.70]:
                count = len(bull_signals[bull_signals[proba_col] >= th])
                logger.info(f"Threshold > {th:.2f}: {count} trades")

    except Exception as e:
        logger.error(f"Erro: {e}")

if __name__ == "__main__":
    analyze()