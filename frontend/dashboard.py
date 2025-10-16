# frontend/dashboard.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- Configurações da Página ---
st.set_page_config(
    page_title="DefiSys Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Título e Cabeçalho ---
st.title("DefiSys - Dashboard de Estratégia DeFi 📈")

# --- Função para buscar dados da nossa API ---
@st.cache_data(ttl=600) # Cache de 10 minutos para os dados
def load_data_from_api():
    API_URL = "http://127.0.0.1:8000/api/v1/run_backtest"
    try:
        # Usar st.spinner para dar um feedback visual durante o carregamento
        with st.spinner("A executar o backtest e a buscar os dados mais recentes... Isto pode demorar um pouco."):
            response = requests.get(API_URL, timeout=300)
            response.raise_for_status()
        st.success("Dados carregados com sucesso!")
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar à API do backend: {e}")
        return None

# --- Função para plotar o gráfico de preços ---
def plot_price_chart(df: pd.DataFrame):
    fig = go.Figure(data=[go.Candlestick(
        x=df['Open_time'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Preço BTC'
    )])
    fig.update_layout(
        title='Preço Histórico do BTC/USDT',
        yaxis_title='Preço (USDT)',
        xaxis_title='Data',
        xaxis_rangeslider_visible=True, # Reativado para melhor navegação
        template='plotly_dark'
    )
    return fig


# --- Carregar os Dados ---
data = load_data_from_api()

# --- Exibir o Dashboard ---
if data:
    report = data['report']
    df_history = pd.DataFrame(data['historical_data'])
    df_history['Open_time'] = pd.to_datetime(df_history['Open_time'])

    # --- Seção de Resumo (KPIs) ---
    st.header("Resultados do Último Backtest")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Resultado da Estratégia", f"${report['profit_usd']:.2f}", f"{report['profit_percentage_usd']:.2f}%")
    col2.metric("Resultado Buy & Hold", f"${(report['btc_benchmark_final_value'] - report['initial_capital_usd']):.2f}", f"{report['btc_benchmark_profit_percentage']:.2f}%")
    col3.metric("Alpha vs. HODL", f"{(report['profit_percentage_usd'] - report['btc_benchmark_profit_percentage']):.2f}%")
    col4.metric("Capital Final", f"${report['final_usd_value']:.2f}")

    st.divider() # Adiciona uma linha divisória

    # --- Estrutura com Abas ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análise Gráfica", "📈 Indicadores Compostos", "📄 Dados Brutos", "🗂️ Histórico de Decisões"])

    with tab1:
        st.plotly_chart(plot_price_chart(df_history), use_container_width=True)

    with tab2:
        st.header("Painel de Indicadores Compostos")
        scores_df = df_history[['Open_time', 'Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']].dropna()
        
        # Renomeia colunas para os gráficos
        scores_df_renamed = scores_df.rename(columns={
            'Open_time': 'index',
            'Sentimento_Score': 'Sentimento (0-1)',
            'Volatilidade_Score': 'Volatilidade (0-1)',
            'Oportunidade_Score': 'Oportunidade (0-1)'
        }).set_index('index')

        st.line_chart(scores_df_renamed)

    with tab3:
        st.header("Dados Históricos Completos")
        st.dataframe(df_history)

    with tab4:
        st.header("Histórico de Decisões")
        # Extrai o histórico de decisões da resposta da API
        decision_history = data.get('decision_history', [])
        if decision_history:
            df_decisions = pd.DataFrame(decision_history)
            # Tenta converter a coluna Data para datetime, se existir
            if 'Data' in df_decisions.columns:
                try:
                    df_decisions['Data'] = pd.to_datetime(df_decisions['Data'])
                except Exception:
                    pass
            st.dataframe(df_decisions)
        else:
            st.info("Nenhum histórico de decisões disponível.")
else:
    st.warning("Não foi possível carregar os dados do backend. Certifique-se de que a API está a rodar com 'make run-api'.")

