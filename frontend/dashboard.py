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

# Create tabs: Strategy Validation, Market X-Ray, and Transaction Log
tab1, tab2, tab3 = st.tabs(["📊 Strategy Validation", "🔍 Market X-Ray", "📜 Diário de Bordo"])

# 1. Busca os dados de Resumo (O Veredicto)
summary = get_data("summary")

with tab1:
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

with tab2:
    st.markdown("### 🔍 Market X-Ray: Análise Ano a Ano")
    
    # Fetch market analysis data
    market_data = get_data("market_analysis")
    
    if market_data and isinstance(market_data, dict) and len(market_data) > 0:
        # Extract years and sort
        years = sorted([int(y) for y in market_data.keys()])
        
        # Year selector
        selected_year = st.selectbox(
            "Selecione o Ano",
            options=years,
            index=len(years) - 1  # Default to most recent year
        )
        
        # Get metrics for selected year
        year_metrics = market_data.get(str(selected_year), {})
        
        if year_metrics:
            # Display metrics in columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Retorno Total",
                    value=f"{year_metrics.get('total_return', 0):.2f}%"
                )
            
            with col2:
                st.metric(
                    label="Max Drawdown",
                    value=f"{year_metrics.get('max_drawdown', 0):.2f}%"
                )
            
            with col3:
                st.metric(
                    label="Maior Pump Dia",
                    value=f"{year_metrics.get('biggest_single_day_pump', 0):.2f}%"
                )
            
            # Display counts
            col4, col5 = st.columns(2)
            
            with col4:
                st.metric(
                    label="Dias Explosivos (>5%)",
                    value=year_metrics.get('explosive_days_count', 0)
                )
            
            with col5:
                st.metric(
                    label="Dias de Queda (<-5%)",
                    value=year_metrics.get('severe_dump_days_count', 0)
                )
            
            st.divider()
            
            # Plot daily returns chart
            st.markdown(f"#### 📈 Retornos Diários de {selected_year}")
            
            daily_returns = year_metrics.get('daily_returns', [])
            
            if daily_returns:
                # Create bar chart with color coding
                colors = []
                for ret in daily_returns:
                    if ret > 5:
                        colors.append('#FFD700')  # Gold for explosive days
                    elif ret > 0:
                        colors.append('#00CC96')  # Green for positive
                    else:
                        colors.append('#EF553B')  # Red for negative
                
                fig_daily = go.Figure(data=[go.Bar(
                    y=daily_returns,
                    marker_color=colors,
                    hovertemplate='<b>Retorno Diário:</b> %{y:.2f}%<extra></extra>'
                )])
                
                fig_daily.update_layout(
                    title=f"Distribuição de Retornos Diários - {selected_year}",
                    yaxis_title="Retorno (%)",
                    xaxis_title="Dia",
                    height=400,
                    showlegend=False,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_daily, use_container_width=True)
                
                # Add legend explanation
                st.markdown("""
                **Cores:**
                - 🟢 Verde: Retorno positivo
                - 🔴 Vermelho: Retorno negativo
                - 🟡 Ouro: Dias explosivos (> 5%)
                """)
            else:
                st.info("Sem dados de retornos diários para este ano.")
        else:
            st.warning(f"Sem dados disponíveis para o ano {selected_year}.")
    else:
        st.info("📊 Carregando dados de análise de mercado...")
        if st.button("Atualizar"):
            st.rerun()

# Tab 3: Transaction Log (V13 Diário de Bordo)
with tab3:
    st.markdown("### 📜 Diário de Bordo: Histórico de Transações")
    
    # Fetch transaction history from API
    trade_history = get_data("trade_history")
    
    if trade_history:
        transactions = trade_history.get("transactions", [])
        total_gas_paid = trade_history.get("total_gas_paid", 0)
        total_transactions = trade_history.get("total_transactions", 0)
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Transações", total_transactions)
        with col2:
            st.metric("Total de Gas Pago", f"${total_gas_paid:.2f}")
        with col3:
            avg_gas = total_gas_paid / total_transactions if total_transactions > 0 else 0
            st.metric("Gas Médio por Transação", f"${avg_gas:.2f}")
        
        st.divider()
        
        if transactions:
            # Convert to DataFrame for display
            df_transactions = pd.DataFrame(transactions)
            
            # Format columns for display
            df_display = df_transactions.copy()
            
            # Format timestamp as DD/MM/YYYY HH:mm (format='mixed' handles varying timestamp formats)
            df_display['timestamp'] = pd.to_datetime(df_display['timestamp'], format='mixed').dt.strftime('%d/%m/%Y %H:%M')
            
            # Format currency columns with $ and 2 decimals
            df_display['btc_price'] = df_display['btc_price'].apply(lambda x: f"${x:,.2f}")
            df_display['usd_amount'] = df_display['usd_amount'].apply(lambda x: f"${x:,.2f}")
            df_display['fee_usd'] = df_display['fee_usd'].apply(lambda x: f"${x:,.2f}")
            df_display['pnl_usd'] = df_display['pnl_usd'].apply(lambda x: f"${x:,.2f}")
            
            # Format BTC amount with 8 decimal places
            df_display['btc_amount'] = df_display['btc_amount'].apply(lambda x: f"{x:.8f}")
            
            # Rename columns for display
            df_display = df_display.rename(columns={
                'timestamp': 'Data/Hora',
                'action': 'Ação',
                'btc_price': 'Preço BTC',
                'usd_amount': 'Valor USD',
                'btc_amount': 'Quantidade BTC',
                'fee_usd': 'Gas Fee',
                'pnl_usd': 'Lucro/Prejuízo',
                'details': 'Detalhes'
            })
            
            # Display the dataframe
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Add transaction details
            st.markdown("#### 📋 Filtros e Análise")
            
            # Filter by action
            actions = df_transactions['action'].unique()
            selected_actions = st.multiselect(
                "Filtrar por tipo de ação",
                options=sorted(actions),
                default=sorted(actions)
            )
            
            # Apply filter
            if selected_actions:
                df_filtered = df_transactions[df_transactions['action'].isin(selected_actions)]
                
                # Show statistics by action
                st.markdown("#### 📊 Estatísticas por Ação")
                action_stats = df_filtered.groupby('action').agg({
                    'usd_amount': 'sum',
                    'btc_amount': 'sum',
                    'fee_usd': 'sum',
                    'pnl_usd': 'sum',
                    'action': 'count'
                }).rename(columns={'action': 'count'})
                
                action_stats['fee_usd'] = action_stats['fee_usd'].apply(lambda x: f"${x:,.2f}")
                action_stats['pnl_usd'] = action_stats['pnl_usd'].apply(lambda x: f"${x:,.2f}")
                action_stats['usd_amount'] = action_stats['usd_amount'].apply(lambda x: f"${x:,.2f}")
                action_stats['btc_amount'] = action_stats['btc_amount'].apply(lambda x: f"{x:.8f}")
                action_stats = action_stats.rename(columns={
                    'usd_amount': 'Total USD',
                    'btc_amount': 'Total BTC',
                    'fee_usd': 'Total Gas',
                    'pnl_usd': 'Total PnL',
                    'count': 'Vezes'
                })
                
                st.dataframe(action_stats, use_container_width=True)
            
        else:
            st.info("Nenhuma transação registrada ainda.")
    
    else:
        st.warning("⚠️ Não foi possível carregar o histórico de transações.")
        if st.button("Tentar Novamente", key="retry_trade_history"):
            st.rerun()
