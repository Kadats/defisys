import asyncio
import logging

from backend.src.utils.ws_manager import manager


class WebSocketHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(manager.broadcast(message))
            except RuntimeError:
                asyncio.run(manager.broadcast(message))
        except Exception:
            self.handleError(record)
