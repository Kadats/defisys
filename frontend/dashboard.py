import streamlit as st
import requests
import pandas as pd

# --- Configurações da Página ---
st.set_page_config(page_title="DefiSys Dashboard", layout="wide")

# --- Título ---
st.title("DefiSys - Dashboard de Estratégia DeFi")

# --- Função para buscar dados da nossa API ---
@st.cache_data # O cache do Streamlit é ótimo para não pedir os dados toda hora
def load_data_from_api():
    API_URL = "http://127.0.0.1:8000/api/v1/run_backtest"
    try:
        response = requests.get(API_URL)
        response.raise_for_status() # Lança um erro se a resposta não for 200 OK
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar à API: {e}")
        return None

# --- Carregar e Exibir os Dados ---
data = load_data_from_api()

if data:
    st.header("Relatório de Performance do Backtest")
    report = data['report']
    
    # Exibir KPIs em colunas
    col1, col2, col3 = st.columns(3)
    col1.metric("Resultado Final", f"${report['final_usd_value']:.2f}", f"{report['profit_percentage_usd']:.2f}%")
    col2.metric("Performance Buy & Hold", f"{report['btc_benchmark_profit_percentage']:.2f}%")
    
    st.json(report) # Exibe o JSON completo do relatório
    
    st.header("Dados Históricos")
    df = pd.DataFrame(data['historical_data'])
    st.dataframe(df) # Exibe o DataFrame interativo

