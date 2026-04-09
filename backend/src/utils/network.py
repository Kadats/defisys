import asyncio
import logging
import functools
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

async def async_execute_with_retry(
    coro_func: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    timeout: float = 5.0,
    retries: int = 3,
    backoff_factor: float = 1.5,
    **kwargs: Any
) -> Any:
    """
    Executa uma corotina com timeout estrito e lógica de retries assíncronos.
    Ideal para chamadas de RPC e APIs externas em ambiente de nuvem.
    """
    last_exception = None
    
    for attempt in range(1, retries + 1):
        try:
            # Aplica o timeout estrito solicitado na Auditoria Nível 2
            return await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
        
        except asyncio.TimeoutError:
            last_exception = Exception(f"Timeout de {timeout}s atingido na tentativa {attempt}/{retries}")
            logger.warning(f"⚠️ {last_exception}")
        
        except Exception as e:
            last_exception = e
            logger.error(f"❌ Erro na tentativa {attempt}/{retries}: {str(e)}")
        
        if attempt < retries:
            sleep_time = backoff_factor ** attempt
            logger.info(f"🔄 Aguardando {sleep_time:.2f}s para nova tentativa...")
            await asyncio.sleep(sleep_time)
            
    logger.critical(f"🚨 Falha crítica após {retries} tentativas: {str(last_exception)}")
    raise last_exception
