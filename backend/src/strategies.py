import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera sinais de trade baseados em uma estratégia de lateralização e sentimento.
    
    Args:
        df (pd.DataFrame): DataFrame contendo os dados OHLCV e os indicadores calculados.
        
    Returns:
        pd.DataFrame: O DataFrame com uma nova coluna 'Signal' e informações do range.
    """
    df_with_signals = df.copy()
    
    # Adiciona uma coluna 'Signal' e a inicializa com 'SEGUIR'
    df_with_signals['Signal'] = 'SEGUIR'
    
    # Adiciona colunas para armazenar o range da pool
    df_with_signals['Pool_Range_Lower'] = None
    df_with_signals['Pool_Range_Upper'] = None
    
    # Lógica da Estratégia (Versão 2.0):
    # A sua estratégia se baseia na ideia de alta oportunidade + baixa volatilidade -> range curto.
    # O Sentimento é um proxy para a 'Oportunidade'.
    
    # Definindo um limite para o Sentimento (ex: 0.5 é neutro, valores abaixo indicam pessimismo)
    SENTIMENT_THRESHOLD = 0.5
    
    # Condição para "ENTRAR EM POOL"
    # Entra na pool quando a volatilidade está baixa (bandas estreitas) E o sentimento não está muito alto (abaixo de 0.5)
    # Isso sugere um bom momento para um range curto, antes que a 'ganância' do mercado aumente.
    df_with_signals.loc[
        (df_with_signals['BB_Upper'] - df_with_signals['BB_Lower'] < df_with_signals['ATR']) &
        (df_with_signals['Sentiment_Score'] < SENTIMENT_THRESHOLD),
        'Signal'
    ] = 'ENTRAR EM POOL'

    # Condição para "SAIR DA POOL"
    # Sai da pool quando a volatilidade aumenta (o preço sai das bandas de Bollinger)
    df_with_signals.loc[
        (df_with_signals['Close'] > df_with_signals['BB_Upper']) |
        (df_with_signals['Close'] < df_with_signals['BB_Lower']),
        'Signal'
    ] = 'SAIR DA POOL'

    # Preenche o range da pool nos sinais de ENTRADA (usando as bandas de bollinger)
    df_with_signals.loc[df_with_signals['Signal'] == 'ENTRAR EM POOL', 'Pool_Range_Lower'] = df_with_signals['BB_Lower']
    df_with_signals.loc[df_with_signals['Signal'] == 'ENTRAR EM POOL', 'Pool_Range_Upper'] = df_with_signals['BB_Upper']
    
    # A coluna Band_Width e Avg_Band_Width são colunas auxiliares que não são necessárias aqui, mas o código original pode ter
    # df_with_signals['Band_Width'] = df_with_signals['BB_Upper'] - df_with_signals['BB_Lower']
    # df_with_signals['Avg_Band_Width'] = df_with_signals['Band_Width'].rolling(window=20).mean()

    return df_with_signals

def get_latest_signal(df: pd.DataFrame) -> str:
    # Apenas retorna o último sinal do DataFrame com a estratégia rodada.
    df_with_signals = generate_signals(df)
    return df_with_signals['Signal'].iloc[-1]

def decide_liquidity(df: pd.DataFrame, sentiment_col: str = 'Sentiment_Score', volatility_col: str = 'Volatility_Score', opportunity_col: str = 'Opportunity_Score') -> pd.Series:
    """
    Decide a ação na pool de liquidez com base nos indicadores compostos.

    Args:
        df (pd.DataFrame): DataFrame com os indicadores compostos.
        sentiment_col (str): Nome da coluna do score de sentimento.
        volatility_col (str): Nome da coluna do score de volatilidade.
        opportunity_col (str): Nome da coluna do score de oportunidade.

    Returns:
        pd.Series: Uma série com a decisão ('range_curto', 'range_largo', 'reduzir').
    """
    if not all(col in df.columns for col in [sentiment_col, volatility_col, opportunity_col]):
        raise ValueError("DataFrame deve conter as colunas dos indicadores compostos.")

    decision = pd.Series('reduzir', index=df.index, dtype='object') # Decisão padrão é reduzir

    # Limiares (thresholds) para a decisão - estes são parâmetros a serem otimizados no backtest
    OPP_HIGH_THRESHOLD = 0.5
    VOL_SAFE_THRESHOLD = 0.3

    # Regra 1: Alta oportunidade + baixa volatilidade -> range curto
    decision.loc[(df[opportunity_col] > OPP_HIGH_THRESHOLD) & (df[volatility_col] < VOL_SAFE_THRESHOLD)] = 'range_curto'
    
    # Regra 2: Alta oportunidade + alta volatilidade -> range largo
    decision.loc[(df[opportunity_col] > OPP_HIGH_THRESHOLD) & (df[volatility_col] >= VOL_SAFE_THRESHOLD)] = 'range_largo'

    return decision

