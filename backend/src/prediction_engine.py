import pandas as pd
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

logger = logging.getLogger(__name__)

# --- 1. DEFINIÇÃO DE FEATURES ---
# Estas são as colunas (indicadores) que o modelo usará para "aprender".
# Nós usamos as features que criamos e coletamos.
FEATURES = [
    'RSI',
    'FNG_Value',
    'dist_from_sma_50',
    'Implied_Volatility',
    'FundingRate',
    'OpenInterest',
    'VolumeUSD'
]

# A coluna que queremos prever
TARGET = 'target_price_fell'

def train_prediction_model(df: pd.DataFrame):
    """
    Treina um modelo de ML (Regressão Logística) para prever quedas de preço.
    """
    logger.info("Iniciando treinamento do modelo de predição V1...")
    
    try:
        X = df[FEATURES]
        y = df[TARGET]
        
        # 1. Divisão de Treino/Teste
        # É CRUCIAL definir 'shuffle=False' para dados de série temporal.
        # Vamos usar os primeiros 80% dos dados para treinar e os últimos 20% para testar.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
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
        
        logger.info(f"--- Relatório de Treinamento do Modelo ---")
        logger.info(f"Modelo: Regressão Logística")
        logger.info(f"Features Usadas: {FEATURES}")
        logger.info(f"Alvo: {TARGET} (Queda > 3% em 7 dias)")
        logger.info(f"Acurácia no Set de Teste (últimos 20% dos dados): {accuracy * 100:.2f}%")
        
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
        
        # Gera a predição (0 ou 1)
        df['prediction'] = model.predict(X_full)
        
        # Compara a predição com o resultado real (para o frontend)
        df['prediction_correct'] = (df['prediction'] == df[TARGET]).astype(int)
        
        logger.info("Predições geradas para o DataFrame.")
        return df
        
    except Exception as e:
        logger.error(f"Falha ao gerar predições: {e}")
        df['prediction'] = 0
        df['prediction_correct'] = 0
        return df

