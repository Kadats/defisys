import logging
import pandas as pd
import numpy as np
import uuid
import os

from backend.src.data.pipeline import get_full_prepared_data
from backend.src.domain.strategies import (
    AccumulatorStrategy,
    BTCLiteStrategy,
    PureSpotStrategy,
    SmartDCAStrategy,
    SwingUSDStrategy,
    build_strategy,
)
from .core import TradingEngine
from .core.policy_layer import PolicyLayerStrategy
from .config import PROJECT_ROOT, ML_TRAIN_SPLIT_DATE, GEMINI_BACKTEST_DAYS

from .ai import train_prediction_model, get_predictions
from backend.src.data import storage
from backend.src.infrastructure.repositories import default_simulation_repository

logger = logging.getLogger(__name__)


# Backward-compatible module-level functions kept patchable by current tests.
def save_predictions_to_db(df: pd.DataFrame) -> None:
    default_simulation_repository.save_predictions(df)


def save_trades(trades_list: list[dict], current_price: float = 0.0) -> None:
    default_simulation_repository.save_trades(trades_list, current_price=current_price)


def save_simulation_summary(**kwargs) -> None:
    default_simulation_repository.save_simulation_summary(**kwargs)

# (A função log_summary_report permanece a mesma)
def log_summary_report(results, latest_indicators=None):
    """
    Registra um resumo do backtest no logger e salva um relatório
    completo em um arquivo .txt.
    """
    
    # --- Parte 1: Logar no Console (REMOVIDA/COMENTADA) ---
    # try:
    #     logger.info("--- RELATORIO DE BACKTEST (v2 Engine) ---")
    #     logger.info("Capital Inicial: $%0.2f", results.get('initial_capital_usd'))
    #     logger.info("Capital Final: $%0.2f", results.get('final_usd_value'))
    #     logger.info("Lucro/Prejuizo: $%0.2f (%0.2f%%)", results.get('profit_usd'), results.get('profit_percentage_usd'))
    #     logger.info("Performance do Buy and Hold (BTC): (%0.2f%%)", results.get('btc_benchmark_profit_percentage'))

    #     if latest_indicators is not None:
    #          cols_to_show = ['Open_time', 'Close', 'FNG_Value', 'RSI', 'Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']
    #          cols_available = [col for col in cols_to_show if col in latest_indicators.columns]
    #          logger.info("--- INDICADORES RECENTES ---")
    #          logger.info("\n%s", latest_indicators[cols_available].to_string())
    # except Exception:
    #     logger.exception("Erro ao logar o sumario do relatorio no console")

    # Backtest summary completed - all results logged to console/logger
    # No .txt file generation needed in V2 architecture


def train_model_pipeline() -> dict:
    """
    Fase 2: Treinamento do Modelo de ML (isolado).
    
    Esta função:
    - Carrega dados preparados do banco de dados (já com indicadores calculados)
    - Faz Split Temporal Walk-Forward (treina até 2023-12-31, testa após)
    - Treina o modelo XGBClassifier
    - Gera predições para todo o histórico
    - Limpa predições antigas do banco
    - Salva novas predições no banco
    
    Esta função NÃO:
    - Coleta dados de APIs externas (isso é feito no startup)
    - Executa backtesting
    - Calcula métricas de trading
    
    Returns:
        dict: Relatório do treinamento com métricas e número de predições geradas
    """
    logger.info("=" * 80)
    logger.info("🤖 FASE 2: INICIANDO TREINAMENTO DO MODELO DE ML")
    logger.info("=" * 80)
    
    # 1. Carregar dados preparados (com indicadores e features)
    logger.info("Carregando dados de mercado e indicadores do banco de dados...")
    full_df = get_full_prepared_data()
    
    if full_df is None or full_df.empty:
        logger.error("Não foi possível obter os dados preparados. Verifique se a Fase 1 foi executada.")
        return {
            "success": False,
            "error": "Failed to load prepared data from database",
            "predictions_generated": 0
        }
    
    logger.info(f"✓ Dados carregados: {len(full_df):,} candles disponíveis")
    
    # 2. Treinar o Modelo com Split Temporal
    logger.info(f"Treinando modelo com Split Temporal (split date: {ML_TRAIN_SPLIT_DATE})...")
    model, scaler = train_prediction_model(full_df, train_test_split_date=ML_TRAIN_SPLIT_DATE)
    
    if model is None or scaler is None:
        logger.error("Falha ao treinar o modelo.")
        return {
            "success": False,
            "error": "Model training failed",
            "predictions_generated": 0
        }
    
    logger.info("✓ Modelo treinado com sucesso")
    
    # 3. Gerar predições para todo o histórico
    logger.info("Gerando predições para todo o histórico...")
    full_df_with_predictions = get_predictions(model, scaler, full_df)
    
    # 4. Limpar predições antigas e salvar novas
    logger.info("Limpando predições antigas do banco de dados...")
    storage.clear_predictions_data()
    
    logger.info("Salvando novas predições no banco de dados...")
    save_predictions_to_db(full_df_with_predictions)
    
    # Contar predições geradas (sinais de compra com threshold)
    predictions_count = int(full_df_with_predictions['prediction'].sum()) if 'prediction' in full_df_with_predictions.columns else 0
    total_candles = len(full_df_with_predictions)
    
    logger.info("=" * 80)
    logger.info("✅ TREINAMENTO DE ML CONCLUÍDO COM SUCESSO!")
    logger.info(f"   Total de candles: {total_candles:,}")
    logger.info(f"   Predições de compra geradas: {predictions_count:,} ({predictions_count/total_candles*100:.1f}%)")
    logger.info("=" * 80)
    
    return {
        "success": True,
        "total_candles": total_candles,
        "predictions_generated": predictions_count,
        "split_date": ML_TRAIN_SPLIT_DATE,
        "model_type": "XGBClassifier"
    }


def run_simulation(
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = None,
    backtest_days: int | None = None,
    strategy_type: str = "accumulator",
    use_llm: bool = False,
) -> dict:
    """
    Fase 3-4: Execução da Simulação de Trading (isolada).
    
    Esta função:
    - Carrega predições de ML do banco de dados (devem existir!)
    - Carrega dados de mercado do banco de dados
    - Faz merge das predições com os dados de mercado
    - Aplica janela temporal (filtro de dias)
    - Executa o TradingEngine com a estratégia escolhida
    - Salva trades, positions e summary no banco
    
    Esta função NÃO:
    - Coleta dados de APIs externas (Fase 1 - feito no startup)
    - Treina modelos de ML (Fase 2 - feito via endpoint separado)
    - Apaga predições de ML do banco
    
    Args:
        start_date: Data inicial da simulação (formato ISO)
        end_date: Data final da simulação (formato ISO)
        initial_capital: Capital inicial em USD
        backtest_days: Número de dias para limitar o backtest
    
    Returns:
        dict: Relatório completo da simulação com métricas de performance
    """
    # 🚀 LOG CLARO DE INÍCIO
    logger.info("=" * 80)
    logger.info("🎯 FASE 3-4: INICIANDO SIMULAÇÃO DE TRADING")
    logger.info(
        f"   Start: {start_date} | End: {end_date} | Capital: ${initial_capital} | "
        f"Days: {backtest_days}"
    )
    logger.info("=" * 80)
    
    # 1. LIMPEZA DE DADOS DE SIMULAÇÃO (NÃO apaga predições de ML)
    storage.clear_simulation_data()
    logger.info("✓ Dados de simulação anteriores limpos (trades, positions, summary)")
    
    # 2. CARREGAR PREDIÇÕES DO BANCO DE DADOS
    logger.info("Carregando predições de ML do banco de dados...")
    predictions_df = default_simulation_repository.get_predictions()
    
    if predictions_df is None or predictions_df.empty:
        logger.error("Nenhuma predição encontrada no banco de dados!")
        logger.error("Execute o treinamento de ML primeiro via POST /api/model/train")
        return {
            "backtest_report": {
                "error": "Modelo não treinado. Por favor, execute o treinamento antes de simular."
            }
        }
    
    logger.info(f"✓ Predições carregadas: {len(predictions_df):,} registros")
    
    # 3. CARREGAR DADOS DE MERCADO DO BANCO
    logger.info("Carregando dados de mercado do banco de dados...")
    from backend.src.data.pipeline import get_full_prepared_data
    full_df = get_full_prepared_data()
    
    if full_df is None or full_df.empty:
        logger.error("Não foi possível carregar dados de mercado do banco.")
        return {
            "backtest_report": {
                "error": "Failed to load market data from database"
            }
        }
    
    logger.info(f"✓ Dados de mercado carregados: {len(full_df):,} candles")
    
    # 4. FAZER MERGE DAS PREDIÇÕES COM OS DADOS DE MERCADO
    logger.info("Fazendo merge de predições com dados de mercado...")
    
    # Garantir que ambos DataFrames tenham Open_time como datetime
    if not pd.api.types.is_datetime64_any_dtype(full_df['Open_time']):
        full_df['Open_time'] = pd.to_datetime(full_df['Open_time'])
    if not pd.api.types.is_datetime64_any_dtype(predictions_df['open_time']):
        predictions_df['open_time'] = pd.to_datetime(predictions_df['open_time'])
    
    # Renomear coluna de predições para fazer merge
    predictions_df = predictions_df.rename(columns={'open_time': 'Open_time'})
    
    # Merge usando Open_time como chave
    full_df_with_predictions = pd.merge(
        full_df,
        predictions_df[['Open_time', 'prediction', 'prediction_proba']],
        on='Open_time',
        how='left'
    )
    
    # Preencher NaN em prediction com 0 (sem sinal de compra)
    full_df_with_predictions['Prediction'] = full_df_with_predictions['prediction'].fillna(0).astype(int)
    full_df_with_predictions['Prediction_Proba'] = full_df_with_predictions['prediction_proba'].fillna(0.5)
    
    logger.info(f"✓ Merge concluído: {len(full_df_with_predictions):,} candles com predições")
    
    # 5. PREPARAR DATAFRAME PARA BACKTEST (Walk-Forward Test Set)
    split_date = pd.Timestamp(ML_TRAIN_SPLIT_DATE)
    simulation_df = full_df_with_predictions[full_df_with_predictions['Open_time'] >= split_date].copy()
    
    # Apply backtest window limit
    effective_days = (
        backtest_days
        if backtest_days is not None
        else (GEMINI_BACKTEST_DAYS if GEMINI_BACKTEST_DAYS > 0 else 30)
    )
    
    if effective_days and effective_days > 0:
        max_date = simulation_df['Open_time'].max()
        min_date = max_date - pd.Timedelta(days=int(effective_days))
        logger.info(
            f"⚠️  BACKTEST_DAYS={int(effective_days)}: "
            f"Limitando backtest aos últimos {int(effective_days)} dias "
            f"({min_date.date()} até {max_date.date()})"
        )
        simulation_df = simulation_df[simulation_df['Open_time'] >= min_date].copy()
    
    # Apply user-defined date filters
    if start_date:
        start_ts = pd.Timestamp(start_date)
        simulation_df = simulation_df[simulation_df['Open_time'] >= start_ts].copy()
    if end_date:
        end_ts = pd.Timestamp(end_date)
        simulation_df = simulation_df[simulation_df['Open_time'] <= end_ts].copy()
    
    simulation_df = simulation_df.reset_index(drop=True)
    
    if simulation_df.empty:
        logger.error("Janela de simulação não produziu dados. Verifique as datas.")
        return {
            "backtest_report": {
                "error": "No data in simulation window"
            }
        }
    
    logger.info(f"✓ Janela de simulação definida: {len(simulation_df):,} candles")
    logger.info(f"  Período: {simulation_df['Open_time'].min().strftime('%Y-%m-%d')} até {simulation_df['Open_time'].max().strftime('%Y-%m-%d')}")
    
    # 6. EXECUTAR O BACKTESTER
    logger.info("Configurando e executando o Trading Engine...")
    engine_initial_capital = float(initial_capital) if initial_capital is not None else 1050.0
    engine = TradingEngine(initial_capital_usd=engine_initial_capital)
    
    # Strategy Factory - instantiate strategy by domain contract
    logger.info(f"Selecionando estratégia: {strategy_type} (LLM: {'ON' if use_llm else 'OFF'})")

    strategy_builders = {
        "accumulator": lambda flag: AccumulatorStrategy(use_llm=flag),
        "btc_lite": lambda _flag: BTCLiteStrategy(),
        "swing_usd": lambda flag: SwingUSDStrategy(use_llm=flag),
        "pure_spot": lambda _flag: PureSpotStrategy(),
        "smart_dca": lambda _flag: SmartDCAStrategy(),
        "policy_layer": lambda flag: PolicyLayerStrategy(use_llm=flag),
    }

    try:
        strategy = build_strategy(
            strategy_type,
            use_llm=use_llm,
            strategy_builders=strategy_builders,
        )
    except ValueError as exc:
        logger.error(f"Estratégia desconhecida: {strategy_type}")
        return {
            "backtest_report": {
                "error": str(exc)
            }
        }
    
    logger.info(f"✓ Estratégia '{strategy_type}' carregada com sucesso")
    
    # Run backtest
    backtest_results = engine.run(simulation_df, strategy=strategy)
    final_equity = float(backtest_results['final_usd_value'])
    roi_percentage = float(backtest_results['profit_percentage_usd'])
    
    # 7. SALVAR TRADES NO BANCO DE DADOS
    logger.info("Salvando trades no banco de dados...")
    price_final = float(simulation_df.iloc[-1]['Close'])
    save_trades(engine.transaction_log, current_price=price_final)
    
    # 8. CALCULAR MÉTRICAS FINAIS
    price_initial = float(simulation_df.iloc[0]['Close'])
    btc_benchmark_profit_percentage = ((price_final - price_initial) / price_initial) * 100
    
    # Calculate Max Drawdown and Sharpe Ratio
    equity_series = pd.Series(engine.portfolio_history)
    max_drawdown = 0.0
    sharpe_ratio = 0.0
    if not equity_series.empty:
        cummax = equity_series.cummax()
        drawdown = (cummax - equity_series) / cummax
        max_drawdown = float(drawdown.max() * 100)
        
        returns = equity_series.pct_change().dropna()
        if not returns.empty and returns.std() != 0:
            # Annualized Sharpe (assuming 6 4h-candles per day, 365 days = 2190 candles/year)
            sharpe_ratio = float((returns.mean() / returns.std()) * np.sqrt(2190))
    
    backtest_results['btc_benchmark_profit_percentage'] = btc_benchmark_profit_percentage
    backtest_results['start_date'] = simulation_df.iloc[0]['Open_time'].isoformat()
    backtest_results['end_date'] = simulation_df.iloc[-1]['Open_time'].isoformat()
    backtest_results['max_drawdown'] = max_drawdown
    backtest_results['sharpe_ratio'] = sharpe_ratio
    
    run_id = str(uuid.uuid4())
    backtest_results['run_id'] = run_id
    
    # Token-based performance metrics
    initial_token_balance = engine.initial_capital / price_initial
    final_token_balance = final_equity / price_final
    token_roi = ((final_token_balance - initial_token_balance) / initial_token_balance) * 100
    alpha_vs_hold = roi_percentage - btc_benchmark_profit_percentage
    
    logger.info(
        f"✓ Equity Total (engine): ${final_equity:.2f}"
    )
    logger.info(f"✓ Benchmark BTC: {btc_benchmark_profit_percentage:.2f}%")
    logger.info(f"✓ ROI Estratégia: {roi_percentage:.2f}%")
    logger.info(f"✓ Alpha vs HOLD: {alpha_vs_hold:.2f}%")
    
    # 9. SALVAR SUMMARY NO BANCO
    logger.info("Salvando summary da simulação no banco de dados...")
    num_trades = len(engine.transaction_log) if engine.transaction_log else 0
    
    # Calculate LP and Aave metrics
    lp_total_value = 0.0
    lp_fees_usd = 0.0
    for lp in engine.active_lps:
        asset_value, _, _ = engine._get_lp_value(lp, price_final)
        asset_value = float(asset_value)
        fees_value = lp.get('fees_accrued_usdt', 0.0) + (lp.get('fees_accrued_btc', 0.0) * price_final)
        lp_total_value += asset_value + fees_value
        lp_fees_usd += fees_value
    
    wallet_spot_total_usd = engine.usd_balance + (engine.btc_hodl_balance * price_final)
    aave_collateral_usd = engine.btc_collateral_balance * price_final
    aave_debt_usd = engine.total_debt_usd
    aave_health_factor = engine.health_factor
    
    save_simulation_summary(
        total_equity=final_equity,
        roi_percent=roi_percentage,
        benchmark_roi_percent=btc_benchmark_profit_percentage,
        total_trades=num_trades,
        initial_capital=engine.initial_capital,
        cash_balance=engine.usd_balance,
        btc_amount=engine.btc_hodl_balance,
        btc_price_final=price_final,
        wallet_spot_total_usd=wallet_spot_total_usd,
        wallet_lp_value_usd=lp_total_value,
        lp_active_count=len(engine.active_lps),
        lp_fees_usd=lp_fees_usd,
        aave_collateral_usd=aave_collateral_usd,
        aave_debt_usd=aave_debt_usd,
        aave_health_factor=aave_health_factor,
        initial_token_balance=initial_token_balance,
        final_token_balance=final_token_balance,
        token_roi=token_roi,
        alpha_vs_hold=alpha_vs_hold
    )
    
    # 10. LOG FINAL
    logger.info("=" * 80)
    logger.info("✅ SIMULAÇÃO CONCLUÍDA COM SUCESSO!")
    logger.info(f"   Trades: {num_trades} | ROI: {roi_percentage:.2f}%")
    logger.info(f"   Equity: ${final_equity:.2f}")
    logger.info("=" * 80)
    
    return {
        "backtest_report": backtest_results
    }


def run_trading_system(
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = None,
    backtest_days: int | None = None,
):
    """
    Orquestra o fluxo de alto nivel: Dados -> Modelo de ML -> Backtest.
    Implementa Walk-Forward: treina em passado distante, testa em passado recente.
    """
    # 🚀 LOG CLARO DE INÍCIO
    logger.info("=" * 80)
    logger.info("🚀 INICIANDO SIMULAÇÃO COM GEMINI + ML WALK-FORWARD")
    logger.info(
        f"   Start: {start_date} | End: {end_date} | Capital: ${initial_capital} | "
        f"Days: {backtest_days}"
    )
    logger.info("=" * 80)
    
    # 1. LIMPEZA ANTES DE COMEÇAR
    storage.clear_simulation_data()
    logger.info("✓ Dados antigos limpos da base")
    
    logger.info("Fase 1: Preparando dados de mercado e indicadores...")

    # 1. Obter os dados (agora com features e alvos de ML)
    logger.info("Fase 1: Preparando todos os dados de mercado e indicadores...")
    full_df = get_full_prepared_data() 
    if full_df is None or full_df.empty:
        logger.error("Não foi possível obter os dados. Encerrando.")
        return {"backtest_report": {"error": "Failed to get data"}, "full_dataframe": pd.DataFrame()} 

    # --- MUDANÇA 2: Treinar o Modelo de ML com Split Temporal ---
    logger.info(f"Fase 2: Treinando o modelo de predição com Split Temporal ({ML_TRAIN_SPLIT_DATE})...")
    model, scaler = train_prediction_model(full_df, train_test_split_date=ML_TRAIN_SPLIT_DATE)
    
    # Gerar predições para todo o histórico (para análise visual)
    full_df_with_predictions = get_predictions(model, scaler, full_df)

    # --- Salvar as predições no DB ---
    logger.info("Fase 2b: Salvando predições no banco de dados...")
    save_predictions_to_db(full_df_with_predictions)

    # 3. Preparar DataFrame para Backtest (Walk-Forward Test Set)
    # CRÍTICO: Usar apenas dados a partir de ML_TRAIN_SPLIT_DATE para o backtest
    split_date = pd.Timestamp(ML_TRAIN_SPLIT_DATE)
    simulation_df = full_df_with_predictions[full_df_with_predictions['Open_time'] >= split_date].copy()
    
    # Apply backtest window limit (use request override if provided, fallback to env, or default to 30 days)
    # CRITICAL: Always enforce a limit to avoid showing data from years ago
    effective_days = (
        backtest_days
        if backtest_days is not None
        else (GEMINI_BACKTEST_DAYS if GEMINI_BACKTEST_DAYS > 0 else 30)
    )
    if effective_days and effective_days > 0:
        max_date = simulation_df['Open_time'].max()
        min_date = max_date - pd.Timedelta(days=int(effective_days))
        logger.warning(
            f"⚠️  BACKTEST_DAYS={int(effective_days)}: "
            f"Limiting backtest to last {int(effective_days)} days "
            f"({min_date.date()} to {max_date.date()}) to avoid API rate limits."
        )
        simulation_df = simulation_df[simulation_df['Open_time'] >= min_date].copy()
    
    if start_date:
        start_ts = pd.Timestamp(start_date)
        simulation_df = simulation_df[simulation_df['Open_time'] >= start_ts].copy()
    if end_date:
        end_ts = pd.Timestamp(end_date)
        simulation_df = simulation_df[simulation_df['Open_time'] <= end_ts].copy()
    simulation_df = simulation_df.reset_index(drop=True)

    if simulation_df.empty:
        logger.error("Simulation window produced no data. Check start/end dates.")
        return {"backtest_report": {"error": "No data in simulation window"}, "full_dataframe": full_df_with_predictions}
    
    logger.info(f"Filtered simulation data. Starting from {split_date}. Rows: {len(simulation_df)}")
    logger.info(f"Fase 3: Configurando Backtest Walk-Forward...")
    logger.info(f"  TREINO (Training Set): até 2023-12-31 | Dataset: {full_df[full_df['Open_time'] < split_date].shape[0]:,} candles")
    logger.info(f"  TESTE (Backtest Set): {simulation_df['Open_time'].min().strftime('%Y-%m-%d')} até {simulation_df['Open_time'].max().strftime('%Y-%m-%d')} | Dataset: {len(simulation_df):,} candles")
    logger.info(f"  ✓ Cobertura do halving/ETFs (2024): Completamente incluída no backtest")
    logger.info(f"  Modelo foi treinado em dados anteriores a {ML_TRAIN_SPLIT_DATE}")
    
    # Configurar e Executar o Backtester apenas com dados pós-split
    logger.info("Fase 4: Executando o backtest da estratégia...")
    # Raised initial capital slightly to provide a healthier buffer for gas + liquidity
    engine_initial_capital = float(initial_capital) if initial_capital is not None else 1050.0
    engine = TradingEngine(initial_capital_usd=engine_initial_capital)
    
    # Instantiate the strategy - Using AccumulatorStrategy (V15 - BTC Maximizer)
    strategy = AccumulatorStrategy()
    
    # O backtester roda APENAS no DataFrame de teste (post-split)
    backtest_results = engine.run(simulation_df, strategy=strategy)
    final_equity = float(backtest_results['final_usd_value'])
    roi_percentage = float(backtest_results['profit_percentage_usd'])
    
    # Salvar os trades no banco de dados
    logger.info("Fase 4b: Salvando trades no banco de dados...")
    price_final = float(simulation_df.iloc[-1]['Close'])
    save_trades(engine.transaction_log, current_price=price_final)
    
    # FIX: Recalcular o benchmark corretamente usando apenas preço do ativo
    price_initial = float(simulation_df.iloc[0]['Close'])
    price_final = float(simulation_df.iloc[-1]['Close'])
    btc_benchmark_profit_percentage = ((price_final - price_initial) / price_initial) * 100
    
    # Atualizar o resultado com o benchmark correto
    backtest_results['btc_benchmark_profit_percentage'] = btc_benchmark_profit_percentage
    
    # FIX: Adicionar metadados de data ao resultado
    backtest_results['start_date'] = simulation_df.iloc[0]['Open_time'].isoformat()
    backtest_results['end_date'] = simulation_df.iloc[-1]['Open_time'].isoformat()
    
    # Calculate Max Drawdown and Sharpe Ratio
    equity_series = pd.Series(engine.portfolio_history)
    max_drawdown = 0.0
    sharpe_ratio = 0.0
    if not equity_series.empty:
        cummax = equity_series.cummax()
        drawdown = (cummax - equity_series) / cummax
        max_drawdown = float(drawdown.max() * 100)
        
        returns = equity_series.pct_change().dropna()
        if not returns.empty and returns.std() != 0:
            sharpe_ratio = float((returns.mean() / returns.std()) * np.sqrt(2190))
    
    run_id = str(uuid.uuid4())
    backtest_results['max_drawdown'] = max_drawdown
    backtest_results['sharpe_ratio'] = sharpe_ratio
    backtest_results['run_id'] = run_id
    
    # ========== NOVAS MÉTRICAS: Token-Based Performance ==========
    # Calcular saldo inicial em tokens (BTC): quanto BTC teríamos se comprássemos tudo no início
    initial_token_balance = engine.initial_capital / price_initial
    
    # Calcular saldo final em tokens (BTC): quanto vale nosso patrimônio hoje em BTC
    final_token_balance = final_equity / price_final
    
    # Calcular ROI em tokens: variação percentual do saldo em tokens
    token_roi = ((final_token_balance - initial_token_balance) / initial_token_balance) * 100
    
    # Calcular Alpha vs HOLD: diferença entre ROI da estratégia e ROI do benchmark
    alpha_vs_hold = roi_percentage - btc_benchmark_profit_percentage
    
    logger.info(
        f"✓ Total Equity (engine): ${final_equity:.2f}"
    )
    logger.info(f"✓ Benchmark BTC recalculado: {btc_benchmark_profit_percentage:.2f}% (Preço: ${price_initial:.2f} → ${price_final:.2f})")
    logger.info(
        f"✓ Token Metrics: Initial={initial_token_balance:.6f} BTC, "
        f"Final={final_token_balance:.6f} BTC, ROI={token_roi:.2f}%, "
        f"Alpha={alpha_vs_hold:.2f}%"
    )

    # ========== FASE 4c: PERSISTIR O SUMMARY OFICIAL ==========
    # Salvar os valores finais OFICIAIS no banco de dados para o Dashboard
    num_trades = len(engine.transaction_log) if engine.transaction_log else 0
    lp_total_value = 0.0
    lp_fees_usd = 0.0
    for lp in engine.active_lps:
        asset_value, _, _ = engine._get_lp_value(lp, price_final)
        asset_value = float(asset_value)
        fees_value = lp.get('fees_accrued_usdt', 0.0) + (lp.get('fees_accrued_btc', 0.0) * price_final)
        lp_total_value += asset_value + fees_value
        lp_fees_usd += fees_value

    wallet_spot_total_usd = engine.usd_balance + (engine.btc_hodl_balance * price_final)
    aave_collateral_usd = engine.btc_collateral_balance * price_final
    aave_debt_usd = engine.total_debt_usd
    aave_health_factor = engine.health_factor

    save_simulation_summary(
        total_equity=final_equity,
        roi_percent=roi_percentage,
        benchmark_roi_percent=btc_benchmark_profit_percentage,
        total_trades=num_trades,
        initial_capital=engine.initial_capital,
        cash_balance=engine.usd_balance,
        btc_amount=engine.btc_hodl_balance,
        btc_price_final=price_final,
        wallet_spot_total_usd=wallet_spot_total_usd,
        wallet_lp_value_usd=lp_total_value,
        lp_active_count=len(engine.active_lps),
        lp_fees_usd=lp_fees_usd,
        aave_collateral_usd=aave_collateral_usd,
        aave_debt_usd=aave_debt_usd,
        aave_health_factor=aave_health_factor,
        initial_token_balance=initial_token_balance,
        final_token_balance=final_token_balance,
        token_roi=token_roi,
        alpha_vs_hold=alpha_vs_hold
    )

    # 4. Logar o relatório final
    latest_indicators = simulation_df.tail(5) if not simulation_df.empty else None
    log_summary_report(backtest_results, latest_indicators)

    logger.info("=" * 80)
    logger.info("✅ SIMULAÇÃO CONCLUÍDA COM SUCESSO!")
    logger.info(f"   Trades: {num_trades} | ROI: {backtest_results['profit_percentage_usd']:.2f}%")
    logger.info(f"   Equity: ${backtest_results['final_usd_value']:.2f}")
    logger.info("=" * 80)
    if not backtest_results:
        backtest_results = {"error": "Backtest execution failed"}
        
    return {
        "backtest_report": backtest_results,
        "full_dataframe": full_df_with_predictions # Retornar o DF completo com as predições
    }
