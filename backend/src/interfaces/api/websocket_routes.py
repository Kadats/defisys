"""WebSocket routes for API interface layer."""

from datetime import datetime
import asyncio
import logging

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.src.utils.ws_manager import manager

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        manager.disconnect(websocket)
        logger.exception("WebSocket error on /ws/logs: %s", exc)


@router.websocket("/api/ws/pulse")
async def websocket_pulse(websocket: WebSocket):
    """Alias para streaming de logs do sistema (System Pulse)."""
    logger.info("Nova tentativa de conexão WebSocket em /api/ws/pulse")
    await manager.connect(websocket)
    logger.info("Cliente conectado com sucesso em /api/ws/pulse")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Cliente desconectado de /api/ws/pulse")
    except (RuntimeError, OSError):
        logger.info("WebSocket /api/ws/pulse encerrado pelo cliente")
    except Exception as exc:
        logger.exception("Erro em /api/ws/pulse: %s", exc)
    finally:
        manager.disconnect(websocket)


@router.websocket("/api/ws/ticker")
async def websocket_ticker(websocket: WebSocket):
    """Stream de Ticker para o Real-Time War Room."""
    logger.info("Nova tentativa de conexão WebSocket em /api/ws/ticker")
    await manager.connect(websocket)
    logger.info("Cliente conectado com sucesso em /api/ws/ticker")
    try:
        while True:
            if (
                websocket.client_state != WebSocketState.CONNECTED
                or websocket.application_state != WebSocketState.CONNECTED
            ):
                break

            await websocket.send_json(
                {
                    "symbol": "BTCUSDT",
                    "price": float(65000 + np.random.normal(0, 100)),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("Cliente desconectado de /api/ws/ticker")
    except (RuntimeError, OSError):
        logger.info("WebSocket /api/ws/ticker encerrado pelo cliente")
    except Exception as exc:
        logger.exception("Erro em /api/ws/ticker: %s", exc)
    finally:
        manager.disconnect(websocket)
