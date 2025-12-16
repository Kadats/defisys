import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import os
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="DefiSys Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONFIGURAÇÃO DE CONEXÃO ---
# Tenta pegar a URL do Docker, fallback para localhost se rodando fora
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# --- FUNÇÕES AUXILIARES ---
def get_data(endpoint, params=None):
    """Função genérica para buscar dados da API com tratamento de erro."""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, timeout=30, params=params) # Timeout maior para backtests
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Não foi possível conectar ao Backend em {API_BASE_URL}. O container está rodando?")
        return None
    except Exception as e:
        st.error(f"❌ Erro ao buscar {endpoint}: {e}")
        return None

# --- LAYOUT DO DASHBOARD ---

st.title("🚀 DefiSys Admin: Painel de Validação")

# 1. Busca os dados de Resumo (O Veredicto)
summary = get_data("summary")

if summary:
    # --- SEÇÃO 1: CABEÇALHO E AÇÃO (KPIs) ---
    st.markdown("### 📡 Status Atual")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Lógica de cor para a ação
    action = summary.get('current_action', 'AGUARDAR')
    action_color = "normal"
    if action == "COMPRAR": action_color = "off" # Streamlit inverte as vezes, mas verde é o ideal
    if action == "ALERTA_RISCO": action_color = "inverse"

    with col1:
        st.metric(label="Ação Sugerida", value=action)
    
    with col2:
        profit = summary.get('net_profit', 0)
        st.metric(label="Lucro Líquido ($)", value=f"${profit:,.2f}", delta=f"{summary.get('strategy_return_pct', 0):.2f}%")
        
    with col3:
        initial = summary.get('initial_capital', 0)
        final = summary.get('final_capital', 0)
        st.metric(label="Capital Final", value=f"${final:,.2f}", delta=f"${final-initial:,.2f}")

    with col4:
        # Comparativo rápido
        strat_ret = summary.get('strategy_return_pct', 0)
        btc_ret = summary.get('btc_hodl_return_pct', 0)
        diff = strat_ret - btc_ret
        st.metric(label="Alpha vs BTC", value=f"{diff:.2f}%", delta="Vencendo" if diff > 0 else "Perdendo")

    st.divider()

    # --- SEÇÃO 2: O VEREDICTO (GRÁFICO) ---
    st.markdown("### ⚖️ O Veredicto: Estratégia vs Bitcoin Hold")
    
    # Nota: Se tivermos equity_curve no futuro, plotamos aqui. 
    # Por enquanto, vamos usar um gráfico de barras comparativo simples.
    fig_verdict = go.Figure()
    fig_verdict.add_trace(go.Bar(
        x=['Minha Estratégia', 'Bitcoin HODL'],
        y=[summary.get('strategy_return_pct', 0), summary.get('btc_hodl_return_pct', 0)],
        marker_color=['#00CC96', '#EF553B'],
        text=[f"{summary.get('strategy_return_pct', 0):.2f}%", f"{summary.get('btc_hodl_return_pct', 0):.2f}%"],
        textposition='auto',
    ))
    fig_verdict.update_layout(title_text="Retorno Total (%)", height=400)
    st.plotly_chart(fig_verdict, use_container_width=True)

    # --- SEÇÃO 3: DETALHES TÉCNICOS ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📊 Gráfico de Preço & Sinais")
        # Sincroniza o gráfico com o período do backtest
        bt_start = summary.get('backtest_start_date')
        bt_end = summary.get('backtest_end_date')
        params = {'start': bt_start, 'end': bt_end} if bt_start and bt_end else None
        chart_data = get_data("chart_data", params=params)
        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            if not df_chart.empty:
                # Converter timestamps se necessário
                fig = go.Figure(data=[go.Candlestick(
                    x=df_chart['Open_time'],
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name="BTC"
                )])
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aguardando dados de gráfico...")

    with col_right:
        st.subheader("📋 Métricas ML & Posições")
        st.write(f"**Acurácia do Modelo:** {summary.get('ml_accuracy', 0)*100:.1f}%")
        st.write(f"**Taxa de Vitória (Win Rate):** {summary.get('win_rate', 0)*100:.1f}%")
        st.write(f"**Última Atualização:** {summary.get('last_updated', 'N/A')}")
        
        if st.button("🔄 Rodar Novo Backtest"):
            with st.spinner("Processando... isso pode levar alguns segundos..."):
                # Força refresh chamando endpoint (se implementarmos lógica de limpar cache)
                # Por enquanto apenas recarrega a página
                time.sleep(1)
                st.rerun()

    # --- SEÇÃO 4: TABELA DE POSIÇÕES ---
    st.subheader("📜 Histórico de Posições")
    positions = get_data("positions")
    if positions:
        closed = positions.get("closed_positions", [])
        if closed:
            df_closed = pd.DataFrame(closed)
            st.dataframe(df_closed, use_container_width=True)
        else:
            st.info("Nenhuma posição fechada ainda.")

else:
    st.warning("⚠️ Nenhum dado de resumo encontrado. O sistema pode estar rodando o primeiro backtest agora...")
    if st.button("Tentar Conectar Novamente"):
        st.rerun()