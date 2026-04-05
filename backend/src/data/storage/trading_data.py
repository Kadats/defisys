import logging
from typing import Optional
import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PGConnection
import pandas as pd

from .connection import create_connection

logger = logging.getLogger(__name__)

# ==================== POSITIONS LOG TABLE ====================

def create_positions_log_table(conn: PGConnection):
    """Creates the 'positions_log' table to track opened and closed LPs."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions_log (
                    id SERIAL PRIMARY KEY,
                    open_timestamp BIGINT NOT NULL,
                    close_timestamp BIGINT,
                    strategy_used TEXT,
                    capital_allocated_usd DOUBLE PRECISION,
                    open_price DOUBLE PRECISION,
                    close_price DOUBLE PRECISION,
                    range_lower DOUBLE PRECISION,
                    range_upper DOUBLE PRECISION,
                    final_profit_usd DOUBLE PRECISION
                )
            """)
            conn.commit()
            logger.info("Table 'positions_log' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating 'positions_log' table: {e}")
        conn.rollback()


def log_open_position(open_timestamp: int, strategy: str, capital_usd: float, 
                     open_price: float, range_lower: float, range_upper: float) -> Optional[int]:
    """
    Records a new opened LP in the database and returns the position ID.
    """
    conn = create_connection()
    if not conn:
        return None
        
    try:
        create_positions_log_table(conn)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO positions_log (open_timestamp, strategy_used, capital_allocated_usd, 
                                         open_price, range_lower, range_upper)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (open_timestamp, strategy, capital_usd, open_price, range_lower, range_upper))
            
            position_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"New position {position_id} registered in 'positions_log'.")
            return position_id
            
    except psycopg2.Error as e:
        logger.error(f"Error registering position opening in DB: {e}")
        conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


def log_close_position(position_id: int, close_timestamp: int, close_price: float, final_profit: float):
    """Updates an existing position with closing data and profit."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE positions_log
                SET close_timestamp = %s,
                    close_price = %s,
                    final_profit_usd = %s
                WHERE id = %s
            """, (close_timestamp, close_price, final_profit, position_id))
            
        conn.commit()
        logger.info(f"Position {position_id} updated with closing data.")
        
    except psycopg2.Error as e:
        logger.error(f"Error registering position closing in DB: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== TRADES TABLE ====================

def create_trades_table(conn: PGConnection):
    """Creates the 'trades' table to store all transaction log data."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    action TEXT NOT NULL,
                    btc_price DOUBLE PRECISION NOT NULL,
                    usd_amount DOUBLE PRECISION DEFAULT 0.0,
                    btc_amount DOUBLE PRECISION DEFAULT 0.0,
                    fee_usd DOUBLE PRECISION DEFAULT 0.0,
                    pnl_usd DOUBLE PRECISION DEFAULT 0.0,
                    post_trade_equity DOUBLE PRECISION DEFAULT 0.0,
                    details TEXT
                )
            """)
            cursor.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS post_trade_equity DOUBLE PRECISION DEFAULT 0.0")
            conn.commit()
            logger.info("Table 'trades' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating 'trades' table: {e}")
        conn.rollback()


def save_trades(trades_list: list, current_price: float = 0.0):
    """
    Salva a lista de trades (transaction_log) no banco de dados.
    Calcula PnL flutuante para posições abertas (Buy Only).
    Limpa os dados antigos antes de inserir os novos.
    
    Args:
        trades_list: Lista de dicionários contendo os dados das transações.
                     Cada dicionário deve ter: timestamp, action, btc_price, 
                     usd_amount, btc_amount, fee_usd, pnl_usd, details
        current_price: Preço atual do BTC para calcular PnL flutuante de posições abertas.
                      Se 0 ou não fornecido, usa o último preço do histórico.
    """
    conn = create_connection()
    if not conn:
        logger.error("Não foi possível conectar ao banco de dados para salvar trades.")
        return
    
    try:
        create_trades_table(conn)
        
        # Limpar trades antigos
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM trades")
            logger.info("Trades antigos removidos da tabela 'trades'.")
        
        # Inserir novos trades
        if not trades_list:
            logger.info("Nenhum trade para salvar.")
            conn.commit()
            return
        
        # Processa cada trade, calculando PnL flutuante para posições abertas
        trades_to_save = []
        for trade in trades_list:
            trade_copy = trade.copy()
            
            # V18: QUANTITATIVE REFINEMENT - Calcular PnL virtual para posições abertas
            # Posições abertas são identificadas por ações de compra sem venda correspondente
            is_buy_action = trade_copy.get("action", "") in ["BUY_HODL", "BUY"]
            btc_amount = float(trade_copy.get("btc_amount", 0))
            entry_price = float(trade_copy.get("btc_price", 0))
            
            # Se é uma posição aberta (compra com BTC > 0) e temos preço atual válido
            if is_buy_action and btc_amount > 0 and entry_price > 0 and current_price > 0:
                # Calcular PnL virtual usando preço atual como "exit_price virtual"
                # PnL = (Preço Atual - Preço de Entrada) × Quantidade
                virtual_pnl_usd = (current_price - entry_price) * btc_amount
                
                # Calcular ROI: (PnL / Capital Investido) × 100%
                capital_invested = entry_price * btc_amount
                virtual_roi_percent = (virtual_pnl_usd / capital_invested * 100) if capital_invested > 0 else 0
                
                # Atualizar o PnL no trade (sem alterar o banco para trades fechados)
                trade_copy["pnl_usd"] = virtual_pnl_usd
                
                # Adicionar tag [OPEN POSITION] nos detalhes para identificação visual
                details = trade_copy.get("details", "")
                if "[OPEN POSITION]" not in details:
                    trade_copy["details"] = (
                        f"[OPEN POSITION] Entry: ${entry_price:.2f} | "
                        f"Current: ${current_price:.2f} | "
                        f"Virtual ROI: {virtual_roi_percent:+.2f}% | {details}"
                    ).strip()
                
                logger.info(
                    f"💼 Virtual PnL calculated: {trade_copy.get('action')} - "
                    f"Entry ${entry_price:.2f} → Current ${current_price:.2f}, "
                    f"Amount {btc_amount:.6f} BTC, PnL ${virtual_pnl_usd:+.2f} (ROI: {virtual_roi_percent:+.2f}%)"
                )
            
            trades_to_save.append(trade_copy)
        
        with conn.cursor() as cursor:
            for trade in trades_to_save:
                # Converter timestamp para formato PostgreSQL
                timestamp = trade.get("timestamp")
                if isinstance(timestamp, pd.Timestamp):
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(timestamp, 'isoformat'):
                    timestamp_str = timestamp.isoformat()
                else:
                    timestamp_str = str(timestamp)
                
                cursor.execute("""
                    INSERT INTO trades (timestamp, action, btc_price, usd_amount, 
                                      btc_amount, fee_usd, pnl_usd, post_trade_equity, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    timestamp_str,
                    trade.get("action", ""),
                    float(trade.get("btc_price", 0)),
                    float(trade.get("usd_amount", 0)),
                    float(trade.get("btc_amount", 0)),
                    float(trade.get("fee_usd", 0)),
                    float(trade.get("pnl_usd", 0)),
                    float(trade.get("post_trade_equity", 0.0)),
                    trade.get("details", "")
                ))
        
        conn.commit()
        logger.info(f"{len(trades_to_save)} trades salvos com sucesso na tabela 'trades'.")
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao salvar trades no banco de dados: {e}")
        conn.rollback()
    except Exception as e:
        logger.error(f"Erro inesperado ao salvar trades: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== SIMULATION UTILS ====================

def clear_simulation_data():
    """
    Limpa as tabelas de simulação (trades, positions, summary) para evitar dados duplicados.
    
    IMPORTANTE: Esta função NÃO apaga as predições de ML (ml_predictions table).
    As predições são gerenciadas separadamente pelo endpoint de treino.
    """
    conn = create_connection()
    if not conn:
        logger.error("Não foi possível conectar ao banco para limpar dados")
        return
    try:
        with conn.cursor() as cursor:
            # Apaga todos os registros de logs de posição
            cursor.execute("DELETE FROM positions_log")
            # Apaga todos os registros de trades
            cursor.execute("DELETE FROM trades")
            # Apaga o summary oficial anterior para forçar nova simulação
            cursor.execute("DELETE FROM simulation_summary")
            # NÃO apaga ml_predictions - isso é feito apenas no treino
        conn.commit()
        logger.info("🧹 Dados de simulação anteriores limpos com sucesso (trades, positions, summary).")
    except Exception as exc:
        logger.error(f"Erro ao limpar dados: {exc}")
        conn.rollback()
    finally:
        conn.close()


# ==================== SIMULATION SUMMARY ====================

def create_simulation_summary_table(conn: PGConnection):
    """Creates simulation_summary table if it doesn't exist."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_summary (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_equity DOUBLE PRECISION NOT NULL,
                    roi_percent DOUBLE PRECISION NOT NULL,
                    benchmark_roi_percent DOUBLE PRECISION NOT NULL,
                    total_trades INTEGER NOT NULL,
                    initial_capital DOUBLE PRECISION NOT NULL,
                    cash_balance DOUBLE PRECISION NOT NULL,
                    btc_amount DOUBLE PRECISION NOT NULL,
                    btc_price_final DOUBLE PRECISION NOT NULL,
                    wallet_spot_total_usd DOUBLE PRECISION,
                    wallet_lp_value_usd DOUBLE PRECISION,
                    lp_active_count INTEGER,
                    lp_fees_usd DOUBLE PRECISION,
                    aave_collateral_usd DOUBLE PRECISION,
                    aave_debt_usd DOUBLE PRECISION,
                    aave_health_factor DOUBLE PRECISION,
                    initial_token_balance DOUBLE PRECISION,
                    final_token_balance DOUBLE PRECISION,
                    token_roi DOUBLE PRECISION,
                    alpha_vs_hold DOUBLE PRECISION
                )
            """)
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS run_id VARCHAR(50)")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS max_drawdown DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS sharpe_ratio DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS wallet_spot_total_usd DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS wallet_lp_value_usd DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS lp_active_count INTEGER")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS lp_fees_usd DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS aave_collateral_usd DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS aave_debt_usd DOUBLE PRECISION")
            cursor.execute("ALTER TABLE simulation_summary ADD COLUMN IF NOT EXISTS aave_health_factor DOUBLE PRECISION")
            conn.commit()
            logger.info("Table 'simulation_summary' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating table 'simulation_summary': {e}")
        conn.rollback()


def save_simulation_summary(
    total_equity: float,
    roi_percent: float,
    benchmark_roi_percent: float,
    total_trades: int,
    initial_capital: float,
    cash_balance: float,
    btc_amount: float,
    btc_price_final: float,
    wallet_spot_total_usd: float,
    wallet_lp_value_usd: float,
    lp_active_count: int,
    lp_fees_usd: float,
    aave_collateral_usd: float,
    aave_debt_usd: float,
    aave_health_factor: float,
    initial_token_balance: float = None,
    final_token_balance: float = None,
    token_roi: float = None,
    alpha_vs_hold: float = None
):
    """Saves the official simulation summary to the database."""
    conn = create_connection()
    if not conn:
        logger.error("Failed to connect to database for saving simulation summary")
        return False
    
    try:
        create_simulation_summary_table(conn)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO simulation_summary 
                (total_equity, roi_percent, benchmark_roi_percent, total_trades,
                 initial_capital, cash_balance, btc_amount, btc_price_final,
                 wallet_spot_total_usd, wallet_lp_value_usd, lp_active_count,
                 lp_fees_usd, aave_collateral_usd, aave_debt_usd, aave_health_factor,
                 initial_token_balance, final_token_balance, token_roi, alpha_vs_hold)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                total_equity,
                roi_percent,
                benchmark_roi_percent,
                total_trades,
                initial_capital,
                cash_balance,
                btc_amount,
                btc_price_final,
                wallet_spot_total_usd,
                wallet_lp_value_usd,
                lp_active_count,
                lp_fees_usd,
                aave_collateral_usd,
                aave_debt_usd,
                aave_health_factor,
                initial_token_balance,
                final_token_balance,
                token_roi,
                alpha_vs_hold
            ))
        
        conn.commit()
        logger.info(
            f"✓ Simulation summary saved: Equity=${total_equity:.2f}, "
            f"ROI={roi_percent:.2f}%, Trades={total_trades}, "
            f"Token ROI={token_roi:.2f}%, Alpha={alpha_vs_hold:.2f}%"
        )
        return True
    except Exception as e:
        logger.error(f"Error saving simulation summary: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_latest_simulation_summary():
    """Retrieves the latest simulation summary from database."""
    conn = create_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    total_equity, roi_percent, benchmark_roi_percent, 
                    total_trades, initial_capital, cash_balance, 
                    btc_amount, btc_price_final, timestamp,
                    wallet_spot_total_usd, wallet_lp_value_usd, lp_active_count,
                    lp_fees_usd, aave_collateral_usd, aave_debt_usd, aave_health_factor,
                    initial_token_balance, final_token_balance,
                    token_roi, alpha_vs_hold
                FROM simulation_summary
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error retrieving simulation summary: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
