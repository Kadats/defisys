import os
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- Configurações da Página ---
st.set_page_config(
    page_title="DefiSys Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Título e Cabeçalho ---
st.title("DefiSys - Dashboard de Posições 📈")
st.caption(f"Dados atualizados em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- Constantes da API ---
# Usa APP_BACKEND_URL se existir, senão cai num default
BACKEND_BASE = os.getenv("APP_BACKEND_URL", "http://localhost:8000")
API_BASE_URL = f"{BACKEND_BASE}/api/v1"

# --- Funções de Carregamento de Dados ---
@st.cache_data(ttl=300) # Cache de 5 minutos
def load_chart_data():
    """Busca dados de velas da API."""
    try:
        response = requests.get(f"{API_BASE_URL}/chart_data", timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            st.error(f"Erro da API ao buscar dados do gráfico: {data['error']}")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df['Open_time'] = pd.to_datetime(df['Open_time'])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar à API para buscar dados do gráfico: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60) # Cache de 1 minuto
def load_positions_data():
    """Busca dados de posições (abertas e fechadas) da API."""
    try:
        response = requests.get(f"{API_BASE_URL}/positions", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        open_df = pd.DataFrame(data.get('open_positions', []))
        closed_df = pd.DataFrame(data.get('closed_positions', []))
        
        # Converte datas para melhor exibição
        if not open_df.empty:
            open_df['open_timestamp'] = pd.to_datetime(open_df['open_timestamp'])
        if not closed_df.empty:
            closed_df['open_timestamp'] = pd.to_datetime(closed_df['open_timestamp'])
            closed_df['close_timestamp'] = pd.to_datetime(closed_df['close_timestamp'])
            
        return open_df, closed_df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar à API para buscar posições: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- Função de Plotagem ---
def plot_price_chart(df: pd.DataFrame, open_positions: pd.DataFrame):
    """Cria o gráfico de velas e plota as posições abertas."""
    fig = go.Figure(data=[go.Candlestick(
        x=df['Open_time'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Preço BTC'
    )])
    
    # Adicionar LPs abertas ao gráfico
    for _, lp in open_positions.iterrows():
        fig.add_hline(
            y=lp['range_lower'],
            line_dash="dot",
            line_color="green",
            annotation_text=f"LP {lp['id']} (Low)",
            annotation_position="bottom right"
        )
        fig.add_hline(
            y=lp['range_upper'],
            line_dash="dot",
            line_color="red",
            annotation_text=f"LP {lp['id']} (High)",
            annotation_position="top right"
        )

    fig.update_layout(
        title='Preço (Últimos 365 dias) e Posições Abertas',
        yaxis_title='Preço (USDT)',
        xaxis_title='Data',
        xaxis_rangeslider_visible=False,
        template='plotly_dark'
    )
    return fig

# --- Carregar os Dados ---
with st.spinner("Carregando dados do gráfico..."):
    df_chart = load_chart_data()
with st.spinner("Carregando dados das posições..."):
    df_open, df_closed = load_positions_data()

# --- Exibir o Dashboard ---
if not df_chart.empty:
    st.plotly_chart(plot_price_chart(df_chart, df_open), use_container_width=True)
else:
    st.warning("Não foi possível carregar os dados do gráfico.")

# --- Abas para Posições ---
st.header("Gerenciamento de Posições")
tab1, tab2 = st.tabs(["Posições Abertas", "Histórico de Posições Fechadas"])

with tab1:
    if not df_open.empty:
        st.dataframe(df_open)
    else:
        st.info("Nenhuma posição aberta no momento.")

with tab2:
    if not df_closed.empty:
        st.dataframe(df_closed)
    else:
        st.info("Nenhum histórico de posições fechadas.")

