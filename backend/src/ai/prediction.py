import pandas as pd
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

from backend.src.config import (
    ML_TRAIN_SPLIT_DATE,
    ML_CONFIDENCE_THRESHOLD
)

logger = logging.getLogger(__name__)

# --- 1. DEFINIÇÃO DE FEATURES ---
# Estas são as colunas (indicadores) que o modelo usará para "aprender".
# Nós usamos as features que criamos e coletamos.
FEATURES = [
    'RSI',
    'dist_from_ema_50',
    'BB_Width',
    'FundingRate',
    'OpenInterest',
    'VolumeUSD'
]

# A coluna que queremos prever
TARGET = 'Target_Trend'

def train_prediction_model(df: pd.DataFrame, train_test_split_date: str = None):
    """
    Treina um modelo de ML (Regressão Logística) para prever altas de preço significativas.
    Usa validação Walk-Forward: treina apenas em dados históricos (antes de train_test_split_date).
    
    O alvo (target) agora é definido como:
    - y = 1 se o preço subir mais de ML_TARGET_MIN_CHANGE% em ML_PREDICTION_HORIZON candles
    - y = 0 caso contrário
    
    Args:
        df: DataFrame com features e target
        train_test_split_date: Data limite (formato "YYYY-MM-DD"). Se None, usa ML_TRAIN_SPLIT_DATE.
    """
    if train_test_split_date is None:
        train_test_split_date = ML_TRAIN_SPLIT_DATE
    
    logger.info("Iniciando treinamento do modelo de predição com Split Temporal...")
    logger.info(f"Configuração ML: Target={TARGET}, Confidence Threshold={ML_CONFIDENCE_THRESHOLD*100}%")
    
    try:
        if TARGET not in df.columns:
            logger.error(f"Target column '{TARGET}' not found in DataFrame. Ensure pipeline creates it.")
            return None, None

        df_with_target = df.dropna(subset=FEATURES + [TARGET]).copy()

        positive_samples = df_with_target[TARGET].sum()
        total_samples = len(df_with_target)
        if total_samples > 0:
            logger.info(
                f"Target disponível: {positive_samples}/{total_samples} ({positive_samples/total_samples*100:.1f}%) amostras positivas"
            )
        
        # Converter a data para datetime se for string
        if isinstance(train_test_split_date, str):
            split_date = pd.to_datetime(train_test_split_date)
        else:
            split_date = train_test_split_date
        
        # 1. Divisão Temporal (Walk-Forward)
        # Treina APENAS com dados antes da data de split (passado "distante")
        train_mask = df_with_target['Open_time'] < split_date
        test_mask = df_with_target['Open_time'] >= split_date
        
        X_train = df_with_target.loc[train_mask, FEATURES]
        y_train = df_with_target.loc[train_mask, TARGET]
        
        X_test = df_with_target.loc[test_mask, FEATURES]
        y_test = df_with_target.loc[test_mask, TARGET]
        
        train_count = len(X_train)
        test_count = len(X_test)
        
        if train_count == 0:
            logger.error(f"Nenhum dado de treino encontrado antes de {train_test_split_date}")
            return None, None
        
        if test_count == 0:
            logger.warning(f"Nenhum dado de teste encontrado a partir de {train_test_split_date}")
        
        # 2. Normalização (Scaling)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 3. Treinamento do Modelo (XGBoost)
        # Ajuste de desbalanceamento
        pos_count = int(y_train.sum())
        neg_count = int(len(y_train) - pos_count)
        scale_pos_weight = (neg_count / pos_count) if pos_count > 0 else 1.0

        model = XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            eval_metric="logloss",
            use_label_encoder=False
        )
        model.fit(X_train_scaled, y_train)
        
        # 4. Avaliação (Nosso "Boletim")
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info("--- Relatório de Treinamento do Modelo (Walk-Forward) ---")
        logger.info("Modelo: XGBClassifier")
        logger.info(f"Features Usadas: {FEATURES}")
        logger.info(f"Alvo: {TARGET} (tendência log-retorno > 2% em 12 candles)")
        logger.info(f"")
        logger.info(f"TREINO (dados históricos):")
        logger.info(f"  Período: {df_with_target.loc[train_mask, 'Open_time'].min().strftime('%Y-%m-%d')} até {df_with_target.loc[train_mask, 'Open_time'].max().strftime('%Y-%m-%d')}")
        logger.info(f"  Amostras: {train_count} velas")
        logger.info(f"")
        logger.info(f"TESTE (backtest walk-forward):")
        logger.info(f"  Período: {df_with_target.loc[test_mask, 'Open_time'].min().strftime('%Y-%m-%d') if test_count > 0 else 'N/A'} até {df_with_target.loc[test_mask, 'Open_time'].max().strftime('%Y-%m-%d') if test_count > 0 else 'N/A'}")
        logger.info(f"  Amostras: {test_count} velas")
        logger.info(f"  Acurácia no Set de Teste: {accuracy * 100:.2f}%")
        
        # 5. Feature importance
        try:
            importances = model.feature_importances_
            ranked = sorted(zip(FEATURES, importances), key=lambda x: x[1], reverse=True)
            logger.info("Feature Importance (desc):")
            for feature, importance in ranked:
                logger.info(f"  {feature}: {importance:.4f}")
        except Exception as e:
            logger.warning(f"Falha ao logar feature importance: {e}")

        # 6. Retorna o modelo treinado e o scaler (para usar em dados novos)
        return model, scaler

    except Exception as e:
        logger.error(f"Falha ao treinar o modelo: {e}")
        return None, None

def get_predictions(model, scaler, df: pd.DataFrame) -> pd.DataFrame:
    """
    Usa um modelo treinado para fazer predições em todo o DataFrame.
    Aplica threshold de confiança: só gera sinal de compra se prob > ML_CONFIDENCE_THRESHOLD.
    """
    if model is None or scaler is None:
        logger.warning("Modelo ou Scaler não fornecido. Pulando predições.")
        df['prediction'] = 0
        df['prediction_proba'] = 0.0
        df['prediction_correct'] = 0
        return df

    try:
        # Prepara todos os dados para a predição
        X_full = df[FEATURES]
        X_full_scaled = scaler.transform(X_full)
        
        # Gera probabilidades para ambas as classes (0 e 1)
        # predict_proba retorna [prob_class_0, prob_class_1]
        probabilities = model.predict_proba(X_full_scaled)
        
        # Extrair a probabilidade da classe 1 (Bullish/Buy Signal)
        df['prediction_proba'] = probabilities[:, 1]
        
        # Aplicar threshold de confiança: só sinaliza compra se prob > ML_CONFIDENCE_THRESHOLD
        df['prediction'] = (df['prediction_proba'] > ML_CONFIDENCE_THRESHOLD).astype(int)
        
        # Estatísticas sobre os sinais gerados
        total_predictions = len(df)
        buy_signals = df['prediction'].sum()
        logger.info(f"Predições geradas: {buy_signals}/{total_predictions} ({buy_signals/total_predictions*100:.1f}%) sinais de compra (prob > {ML_CONFIDENCE_THRESHOLD*100}%)")
        
        # Compara a predição com o resultado real (para o frontend)
        if TARGET in df.columns:
            df['prediction_correct'] = (df['prediction'] == df[TARGET]).astype(int)
        else:
            df['prediction_correct'] = 0
        
        logger.info("Predições com threshold de confiança aplicadas ao DataFrame.")
        return df
        
    except Exception as e:
        logger.error(f"Falha ao gerar predições: {e}")
        df['prediction'] = 0
        df['prediction_proba'] = 0.0
        df['prediction_correct'] = 0
        return df

