import pandas as pd
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from datetime import datetime

logger = logging.getLogger(__name__)

# --- 1. DEFINIÇÃO DE FEATURES ---
# Estas são as colunas (indicadores) que o modelo usará para "aprender".
# Nós usamos as features que criamos e coletamos.
FEATURES = [
    'RSI',
    'FNG_Value',
    'dist_from_sma_50',
    'dist_from_sma_200',
    'Implied_Volatility',
    'FundingRate',
    'OpenInterest',
    'VolumeUSD',
    'MACD', 
    'MACD_Histogram', # Ajuda a ver a virada de tendência
    'ATR',            # Volatilidade absoluta
    'BB_Position',    # Preço relativo às bandas (sobrecompra/venda)
    'Stoch_K',        # Momentum rápido
    'OBV'             # Fluxo de volume acumulado
]

# A coluna que queremos prever
TARGET = 'target_price_rise'

def train_prediction_model(df: pd.DataFrame, train_test_split_date: str = "2022-01-01"):
    """
    Treina um modelo de ML (Regressão Logística) para prever altas de preço (oportunidades de compra).
    Usa validação Walk-Forward: treina apenas em dados históricos (antes de train_test_split_date).
    
    Args:
        df: DataFrame com features e target
        train_test_split_date: Data limite (formato "YYYY-MM-DD"). Treina antes, testa depois.
    """
    logger.info("Iniciando treinamento do modelo de predição com Split Temporal (Walk-Forward)...")
    
    try:
        # Converter a data para datetime se for string
        if isinstance(train_test_split_date, str):
            split_date = pd.to_datetime(train_test_split_date)
        else:
            split_date = train_test_split_date
        
        # 1. Divisão Temporal (Walk-Forward)
        # Treina APENAS com dados antes da data de split (passado "distante")
        train_mask = df['Open_time'] < split_date
        test_mask = df['Open_time'] >= split_date
        
        X_train = df.loc[train_mask, FEATURES]
        y_train = df.loc[train_mask, TARGET]
        
        X_test = df.loc[test_mask, FEATURES]
        y_test = df.loc[test_mask, TARGET]
        
        train_count = len(X_train)
        test_count = len(X_test)
        
        if train_count == 0:
            logger.error(f"Nenhum dado de treino encontrado antes de {train_test_split_date}")
            return None, None
        
        if test_count == 0:
            logger.warning(f"Nenhum dado de teste encontrado a partir de {train_test_split_date}")
        
        # 2. Normalização (Scaling)
        # Modelos de ML funcionam melhor quando todos os números estão na mesma escala
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 3. Treinamento do Modelo
        # Regressão Logística é um modelo simples, rápido e ótimo para começar.
        model = LogisticRegression(random_state=42)
        model.fit(X_train_scaled, y_train)
        
        # 4. Avaliação (Nosso "Boletim")
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"--- Relatório de Treinamento do Modelo (Walk-Forward) ---")
        logger.info(f"Modelo: Regressão Logística")
        logger.info(f"Features Usadas: {FEATURES}")
        logger.info(f"Alvo: {TARGET} (Subida > 3% em 7 dias - Oportunidades de Compra)")
        logger.info(f"")
        logger.info(f"TREINO (dados históricos):")
        logger.info(f"  Período: {df.loc[train_mask, 'Open_time'].min().strftime('%Y-%m-%d')} até {df.loc[train_mask, 'Open_time'].max().strftime('%Y-%m-%d')}")
        logger.info(f"  Amostras: {train_count} velas")
        logger.info(f"")
        logger.info(f"TESTE (backtest walk-forward):")
        logger.info(f"  Período: {df.loc[test_mask, 'Open_time'].min().strftime('%Y-%m-%d') if test_count > 0 else 'N/A'} até {df.loc[test_mask, 'Open_time'].max().strftime('%Y-%m-%d') if test_count > 0 else 'N/A'}")
        logger.info(f"  Amostras: {test_count} velas")
        logger.info(f"  Acurácia no Set de Teste: {accuracy * 100:.2f}%")
        
        # 5. Retorna o modelo treinado e o scaler (para usar em dados novos)
        return model, scaler

    except Exception as e:
        logger.error(f"Falha ao treinar o modelo: {e}")
        return None, None

def get_predictions(model, scaler, df: pd.DataFrame) -> pd.DataFrame:
    """
    Usa um modelo treinado para fazer predições em todo o DataFrame.
    """
    if model is None or scaler is None:
        logger.warning("Modelo ou Scaler não fornecido. Pulando predições.")
        df['prediction'] = 0
        df['prediction_correct'] = 0
        return df

    try:
        # Prepara todos os dados para a predição
        X_full = df[FEATURES]
        X_full_scaled = scaler.transform(X_full)
        
        # Gera a predição (0 ou 1) usando os dados normalizados
        df['prediction'] = model.predict(X_full_scaled)
        
        # Compara a predição com o resultado real (para o frontend)
        df['prediction_correct'] = (df['prediction'] == df[TARGET]).astype(int)
        
        logger.info("Predições geradas para o DataFrame.")
        return df
        
    except Exception as e:
        logger.error(f"Falha ao gerar predições: {e}")
        df['prediction'] = 0
        df['prediction_correct'] = 0
        return df

