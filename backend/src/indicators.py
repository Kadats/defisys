import pandas as pd
import numpy as np

# Indicadores de Tendência (Trend Indicators)
def calculate_sma(df: pd.DataFrame, column: str = 'Close', window: int = 20) -> pd.Series:
    """
    Calcula a Média Móvel Simples (SMA) para uma coluna específica de um DataFrame.
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de preço.
        column (str): Nome da coluna para calcular a SMA (padrão: 'Close').
        window (int): Período da média móvel (ex: 20 para SMA de 20 dias).

    Returns:
        pd.Series: Uma Série Pandas com os valores da SMA.
    """
    if column not in df.columns:
        raise ValueError(f"Coluna '{column}' não encontrada no DataFrame.")
    
    return df[column].rolling(window=window).mean()

def calculate_ema(df: pd.DataFrame, column: str = 'Close', window: int = 20) -> pd.Series:
    """
    Calcula a Média Móvel Exponencial (EMA) para uma coluna específica de um DataFrame.
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de preço.
        column (str): Nome da coluna para calcular a EMA (padrão: 'Close').
        window (int): Período da média móvel (ex: 20 para EMA de 20 dias).

    Returns:
        pd.Series: Uma Série Pandas com os valores da EMA.
    """
    if column not in df.columns:
        raise ValueError(f"Coluna '{column}' não encontrada no DataFrame.")
    
    return df[column].ewm(span=window, adjust=False).mean()

def calculate_macd(df: pd.DataFrame, column: str = 'Close', fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    """
    Calcula o Moving Average Convergence Divergence (MACD).
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de preço.
        column (str): Nome da coluna para calcular o MACD (padrão: 'Close').
        fast_period (int): Período da EMA rápida (padrão: 12).
        slow_period (int): Período da EMA lenta (padrão: 26).
        signal_period (int): Período da linha de sinal (padrão: 9).

    Returns:
        pd.DataFrame: Um DataFrame com as colunas 'MACD', 'MACD_Signal' e 'MACD_Histogram'.
    """
    if column not in df.columns:
        raise ValueError(f"Coluna '{column}' não encontrada no DataFrame.")
    
    # Calcular EMA rápida e lenta
    exp1 = df[column].ewm(span=fast_period, adjust=False).mean()
    exp2 = df[column].ewm(span=slow_period, adjust=False).mean()
    
    # Calcular Linha MACD
    macd_line = exp1 - exp2
    
    # Calcular Linha de Sinal (EMA da Linha MACD)
    macd_signal = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Calcular Histograma MACD
    macd_histogram = macd_line - macd_signal
    
    macd_df = pd.DataFrame({
        'MACD': macd_line,
        'MACD_Signal': macd_signal,
        'MACD_Histogram': macd_histogram
    }, index=df.index) # Use o mesmo índice do DataFrame original
    
    return macd_df

def calculate_bollinger_bands(df: pd.DataFrame, column: str = 'Close', window: int = 20, num_std_dev: int = 2) -> pd.DataFrame:
    """
    Calcula as Bandas de Bollinger.
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de preço.
        column (str): Nome da coluna para calcular as Bandas de Bollinger (padrão: 'Close').
        window (int): Período da Média Móvel central (padrão: 20).
        num_std_dev (int): Número de desvios padrão para as bandas superior e inferior (padrão: 2).

    Returns:
        pd.DataFrame: Um DataFrame com as colunas 'BB_Middle', 'BB_Upper' e 'BB_Lower'.
    """
    if column not in df.columns:
        raise ValueError(f"Coluna '{column}' não encontrada no DataFrame.")
    
    # Calcular a Banda Média (SMA)
    middle_band = df[column].rolling(window=window).mean()
    
    # Calcular o desvio padrão móvel
    std_dev = df[column].rolling(window=window).std()
    
    # Calcular as Bandas Superior e Inferior
    upper_band = middle_band + (std_dev * num_std_dev)
    lower_band = middle_band - (std_dev * num_std_dev)
    
    bb_df = pd.DataFrame({
        'BB_Middle': middle_band,
        'BB_Upper': upper_band,
        'BB_Lower': lower_band
    }, index=df.index) # Use o mesmo índice do DataFrame original
    
    return bb_df

def calculate_fibonacci_retracements(df: pd.DataFrame, high_col: str = 'High', low_col: str = 'Low', window: int = 60) -> pd.DataFrame:
    """
    Calcula os níveis de Retracements de Fibonacci para um período.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados OHLCV.
        high_col (str): Nome da coluna de preços máximos (padrão: 'High').
        low_col (str): Nome da coluna de preços mínimos (padrão: 'Low').
        window (int): Período para buscar o topo e o fundo (padrão: 60 dias).

    Returns:
        pd.DataFrame: Um DataFrame com as colunas dos níveis de Fibonacci (23.6, 38.2, 50.0, 61.8, 78.6).
    """
    if not all(col in df.columns for col in [high_col, low_col]):
        raise ValueError(f"DataFrame deve conter as colunas '{high_col}' e '{low_col}'.")
    
    # Identificar o topo e o fundo no período da janela
    fib_df = df.copy()
    fib_df['High_Window'] = fib_df[high_col].rolling(window=window).max()
    fib_df['Low_Window'] = fib_df[low_col].rolling(window=window).min()
    
    # Calcular a amplitude do movimento (Range)
    fib_range = fib_df['High_Window'] - fib_df['Low_Window']
    
    # Calcular os níveis de retracement
    fib_df['Fib_23_6'] = fib_df['High_Window'] - fib_range * 0.236
    fib_df['Fib_38_2'] = fib_df['High_Window'] - fib_range * 0.382
    fib_df['Fib_50_0'] = fib_df['High_Window'] - fib_range * 0.500
    fib_df['Fib_61_8'] = fib_df['High_Window'] - fib_range * 0.618
    
    return fib_df[['Fib_23_6', 'Fib_38_2', 'Fib_50_0', 'Fib_61_8']]

# Indicadores de Momentum (Momentum Indicators)
def calculate_rsi(df: pd.DataFrame, column: str = 'Close', window: int = 14) -> pd.Series:
    """
    Calcula o Índice de Força Relativa (RSI) para uma coluna específica de um DataFrame.
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de preço.
        column (str): Nome da coluna para calcular o RSI (padrão: 'Close').
        window (int): Período do RSI (padrão: 14).

    Returns:
        pd.Series: Uma Série Pandas com os valores do RSI.
    """
    if column not in df.columns:
        raise ValueError(f"Coluna '{column}' não encontrada no DataFrame.")
    
    # Calcular a variação de preço diária
    delta = df[column].diff(1)
    
    # Separar ganhos (preço subiu) e perdas (preço caiu)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0) # Perdas são valores positivos
    
    # Calcular a média móvel exponencial de ganhos e perdas
    avg_gain = gain.ewm(span=window, adjust=False).mean()
    avg_loss = loss.ewm(span=window, adjust=False).mean()
    
    # Calcular Relative Strength (RS)
    # Evitar divisão por zero para avg_loss
    rs = avg_gain / avg_loss.replace(0, 1e-9) # Pequeno valor para evitar Div/0

    # Calcular RSI
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_stochastic_oscillator(df: pd.DataFrame, high_col: str = 'High', low_col: str = 'Low', close_col: str = 'Close', k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
    """
    Calcula o Oscilador Estocástico (%K e %D).
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados OHLCV.
        high_col (str): Nome da coluna de preços máximos (padrão: 'High').
        low_col (str): Nome da coluna de preços mínimos (padrão: 'Low').
        close_col (str): Nome da coluna de preços de fechamento (padrão: 'Close').
        k_window (int): Período para %K (padrão: 14).
        d_window (int): Período para %D (SMA de %K) (padrão: 3).

    Returns:
        pd.DataFrame: Um DataFrame com as colunas '%K' e '%D'.
    """
    if not all(col in df.columns for col in [high_col, low_col, close_col]):
        raise ValueError("DataFrame deve conter as colunas 'High', 'Low' e 'Close'.")
    
    # Calcular o valor mais alto e mais baixo no período %K
    lowest_low = df[low_col].rolling(window=k_window).min()
    highest_high = df[high_col].rolling(window=k_window).max()
    
    # Calcular %K
    # Evitar divisão por zero
    k_line = ((df[close_col] - lowest_low) / (highest_high - lowest_low)).fillna(0) * 100
    
    # Calcular %D (SMA de %K)
    d_line = k_line.rolling(window=d_window).mean()
    
    stoch_df = pd.DataFrame({
        'Stoch_K': k_line,
        'Stoch_D': d_line
    }, index=df.index)
    
    return stoch_df

# Indicadores de Volume (Volume Indicators)
def calculate_obv(df: pd.DataFrame, close_col: str = 'Close', volume_col: str = 'Volume') -> pd.Series:
    """
    Calcula o On-Balance Volume (OBV).
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de preço e volume.
        close_col (str): Nome da coluna de preços de fechamento (padrão: 'Close').
        volume_col (str): Nome da coluna de volume (padrão: 'Volume').

    Returns:
        pd.Series: Uma Série Pandas com os valores do OBV.
    """
    if not all(col in df.columns for col in [close_col, volume_col]):
        raise ValueError("DataFrame deve conter as colunas 'Close' e 'Volume'.")
    
    # Calcular a mudança de preço (positivo se subiu, negativo se desceu)
    price_change = df[close_col].diff()
    
    # Inicializar o OBV com 0
    obv = pd.Series(0, index=df.index, dtype='float64')
    
    # Iterar sobre as mudanças de preço para calcular o OBV
    # (Pode ser otimizado com operações vetorizadas do Pandas em datasets muito grandes)
    for i in range(1, len(df)):
        if price_change.iloc[i] > 0: # Se o preço subiu
            obv.iloc[i] = obv.iloc[i-1] + df[volume_col].iloc[i]
        elif price_change.iloc[i] < 0: # Se o preço desceu
            obv.iloc[i] = obv.iloc[i-1] - df[volume_col].iloc[i]
        else: # Se o preço não mudou
            obv.iloc[i] = obv.iloc[i-1]
            
    return obv

# Indicadores de Volatilidade (Volatility Indicators)
def calculate_atr(df: pd.DataFrame, high_col: str = 'High', low_col: str = 'Low', close_col: str = 'Close', window: int = 14) -> pd.Series:
    """
    Calcula o Average True Range (ATR).
    Assume que o DataFrame já está ordenado por 'Open_time' em ordem crescente.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados OHLCV.
        high_col (str): Nome da coluna de preços máximos (padrão: 'High').
        low_col (str): Nome da coluna de preços mínimos (padrão: 'Low').
        close_col (str): Nome da coluna de preços de fechamento (padrão: 'Close').
        window (int): Período para o ATR (padrão: 14).

    Returns:
        pd.Series: Uma Série Pandas com os valores do ATR.
    """
    if not all(col in df.columns for col in [high_col, low_col, close_col]):
        raise ValueError("DataFrame deve conter as colunas 'High', 'Low' e 'Close'.")

    # Calcular o True Range (TR)
    # TR é o maior entre:
    # 1. High atual - Low atual
    # 2. |High atual - Close anterior|
    # 3. |Low atual - Close anterior|
    
    high_low = df[high_col] - df[low_col]
    high_close_prev = abs(df[high_col] - df[close_col].shift())
    low_close_prev = abs(df[low_col] - df[close_col].shift())
    
    # O .max(axis=1) garante que pegamos o maior valor de cada linha
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    
    # O ATR é a Média Móvel Exponencial (EMA) do TR
    atr = tr.ewm(span=window, adjust=False).mean()
    
    return atr

# Indicadores Compostos
def calculate_composite_sentiment(funding_rate: pd.Series, open_interest: pd.Series) -> pd.Series:
    """
    Calcula um indicador composto de sentimento.
    Baseado em Funding Rate (0.6) e Open Interest (0.4), conforme blueprint.

    Args:
        funding_rate (pd.Series): Série de dados do Funding Rate.
        open_interest (pd.Series): Série de dados de Open Interest.

    Returns:
        pd.Series: Uma Série Pandas com o score de sentimento.
    """
    # Lógica de pesos do blueprint: Sentimento = (Funding Rate * 0.6) + (Open Interest * 0.4)
    
    # Normalizar o Funding Rate (evitar divisão por zero)
    funding_range = funding_rate.max() - funding_rate.min()
    if funding_range == 0:
        normalized_funding = pd.Series(0, index=funding_rate.index)
    else:
        normalized_funding = (funding_rate - funding_rate.min()) / funding_range
    
    # Normalizar o Open Interest (evitar divisão por zero)
    oi_range = open_interest.max() - open_interest.min()
    if oi_range == 0:
        normalized_open_interest = pd.Series(0, index=open_interest.index)
    else:
        normalized_open_interest = (open_interest - open_interest.min()) / oi_range
    
    # Aplicar os pesos
    sentiment_score = (normalized_funding * 0.6) + (normalized_open_interest * 0.4)
    
    return sentiment_score

def calculate_composite_volatility(df: pd.DataFrame, iv_col: str = 'Implied_Volatility', atr_col: str = 'ATR') -> pd.Series:
    """
    Calcula o indicador composto de volatilidade usando Implied Volatility (IV) como fonte
    primária. O ATR foi removido da lógica — o IV (Deribit BTC_DVOL) fornece um sinal mais
    preditivo e alinhado com o blueprint.

    Args:
        df (pd.DataFrame): DataFrame contendo a coluna de Implied Volatility.
        iv_col (str): Nome da coluna para a Volatilidade Implícita (padrão: 'Implied_Volatility').

    Returns:
        pd.Series: Série Pandas com o score de volatilidade normalizado entre 0 e 1.
    """
    # Preferir Implied Volatility se disponível e não totalmente nula
    if iv_col in df.columns and not df[iv_col].isnull().all():
        iv_series = df[iv_col].astype(float)
        iv_min = iv_series.min()
        iv_max = iv_series.max()
        if iv_max == iv_min:
            return pd.Series(0.5, index=df.index)
        return (iv_series - iv_min) / (iv_max - iv_min)

    # Caso IV não esteja disponível, usar ATR como fallback (mantém compatibilidade)
    if atr_col in df.columns and not df[atr_col].isnull().all():
        atr_series = df[atr_col].astype(float)
        atr_min = atr_series.min()
        atr_max = atr_series.max()
        if atr_max == atr_min:
            return pd.Series(0.5, index=df.index)
        return (atr_series - atr_min) / (atr_max - atr_min)

    raise ValueError(f"Nenhuma das colunas '{iv_col}' ou '{atr_col}' está disponível no DataFrame para calcular volatilidade.")

def calculate_composite_opportunity(df: pd.DataFrame, volume_onchain_col: str = 'VolumeUSD', tvl_col: str = 'TVL_USD') -> pd.Series:
    """
    Calcula o Oportunidade_Score usando dados on-chain da Uniswap v3 conforme o blueprint:

    Score = 0.5 * normalized(volumeUSD) + 0.5 * normalized(utilization)

    onde utilization = volumeUSD / tvlUSD (por dia).

    A função normaliza cada série para 0..1; se a série for constante ou vazia, usa 0.5 como fallback.
    """
    # Preferir dados on-chain da Uniswap quando disponíveis
    if volume_onchain_col in df.columns and tvl_col in df.columns:
        vol = df[volume_onchain_col].fillna(0).astype(float)
        tvl = df[tvl_col].fillna(0).astype(float)

        # Evitar divisão por zero ao calcular utilization
        utilization = vol / tvl.replace(0, np.nan)
        utilization = utilization.fillna(0.0)

        # Normalize helper
        def normalize_series(s: pd.Series) -> pd.Series:
            s_min = s.min()
            s_max = s.max()
            if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
                return pd.Series(0.5, index=s.index)
            return (s - s_min) / (s_max - s_min)

        vol_n = normalize_series(vol)
        util_n = normalize_series(utilization)

        opportunity_score = 0.5 * vol_n + 0.5 * util_n
        return opportunity_score

    # Fallback: use on-exchange volume column if present
    if 'Volume' in df.columns:
        v = df['Volume'].fillna(0).astype(float)
        v_min = v.min()
        v_max = v.max()
        if v_max == v_min:
            return pd.Series(0.5, index=df.index)
        return (v - v_min) / (v_max - v_min)

    raise ValueError("Nenhuma fonte de volume disponível para calcular Oportunidade_Score.")

