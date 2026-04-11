import asyncio
import logging
import requests
import json
from dataclasses import dataclass
from typing import List, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class RPCNode:
    url: str
    priority: int
    is_healthy: bool = True
    name: str = "Unknown"
    latency: float = 0.0

class RPCManager:
    """
    Gerencia Multi-RPC Failover para resiliência institucional.
    Implementa o Nível 2.1 da Auditoria de Infraestrutura.
    """
    def __init__(
        self, 
        primary_url: str = "", 
        secondary_url: str = "", 
        decentralized_url: str = "",
        timeout: float = 5.0
    ):
        self.nodes: List[RPCNode] = []
        if primary_url:
            self.nodes.append(RPCNode(url=primary_url, priority=1, name="PRIMARY"))
        if secondary_url:
            self.nodes.append(RPCNode(url=secondary_url, priority=2, name="SECONDARY"))
        if decentralized_url:
            self.nodes.append(RPCNode(url=decentralized_url, priority=3, name="DECENTRALIZED"))
        
        self.timeout = timeout
        self._active_node_index = 0
        logger.info(f"RPCManager inicializado com {len(self.nodes)} nós configurados.")

    def get_all_health(self) -> dict:
        """Retorna o estado de saúde e latência de todos os nós (para o Control Center)."""
        return {
            node.name.lower(): {
                "status": "ok" if node.is_healthy else "error",
                "latency": round(node.latency * 1000, 2),  # em ms
                "url": node.url[:25] + "..." if len(node.url) > 25 else node.url
            }
            for node in self.nodes
        }

    def get_active_rpc(self) -> Optional[RPCNode]:
        """Retorna o nó RPC ativo atual (o primeiro saudável disponível)."""
        for node in self.nodes:
            if node.is_healthy:
                return node
        return None

    async def _make_request(self, url: str, payload: dict) -> dict:
        """Transporte assíncrono básico para chamadas RPC."""
        # Como o projeto usa requests para sources, mantemos consistência ou usamos loop para async.
        # Mas para o failover funcionar com timeout estrito de 5s:
        loop = asyncio.get_event_loop()
        headers = {"Content-Type": "application/json"}
        
        # Chamada requests dentro do executor para não bloquear o loop de eventos
        def post():
            return requests.post(url, data=json.dumps(payload), headers=headers, timeout=self.timeout)

        start_time = asyncio.get_event_loop().time()
        response = await loop.run_in_executor(None, post)
        end_time = asyncio.get_event_loop().time()
        
        response.raise_for_status()
        result = response.json()
        result["_latency"] = end_time - start_time
        return result

    async def perform_health_check(self):
        """Realiza um health check rápido (eth_blockNumber) em todos os nós."""
        logger.info("Executando Health Check em todos os nós RPC...")
        payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
        
        for node in self.nodes:
            try:
                # Usando o transporte interno com timeout
                response = await self._make_request(node.url, payload)
                node.is_healthy = True
                node.latency = response.get("_latency", 0.0)
                logger.info(f"✓ Nó {node.name} está SAUDÁVEL ({round(node.latency*1000)}ms).")
            except Exception as e:
                node.is_healthy = False
                node.latency = 0.0
                logger.warning(f"❌ Nó {node.name} está OFFLINE: {str(e)}")
        
        # Garante que o índice ativo seja redefinido para o primeiro saudável
        for i, node in enumerate(self.nodes):
            if node.is_healthy:
                self._active_node_index = i
                break

    async def call(self, method: str, params: list = None) -> Any:
        """Executa uma chamada RPC com lógica de failover automática."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": int(asyncio.get_event_loop().time() * 1000)
        }

        # Tentamos todos os nós disponíveis se houver falhas
        for attempt_node in range(len(self.nodes)):
            active_node = self.get_active_rpc()
            
            if not active_node:
                logger.critical("🚨 NENHUM RPC SAUDÁVEL DISPONÍVEL NO RPCManager!")
                raise Exception("Sem nós RPC disponíveis")

            try:
                # Implementação do timeout de 5s solicitado na auditoria (já embutido no _make_request)
                response_json = await self._make_request(active_node.url, payload)
                
                if "error" in response_json:
                    raise Exception(f"RPC Error ({active_node.name}): {response_json['error']}")
                
                return response_json.get("result")

            except (asyncio.TimeoutError, requests.exceptions.RequestException, Exception) as e:
                # LOG DE OBSERVALIBIDADE SOLICITADO
                logger.warning(f"⚠️ Erro no nó {active_node.name} ({active_node.url}): {str(e)}")
                active_node.is_healthy = False
                
                # Procura o próximo nó
                next_node = self.get_active_rpc()
                if next_node:
                    logger.info(f"[RPC_INFO] Switched to {next_node.name} RPC due to failure on {active_node.name}.")
                else:
                    logger.error(f"🚨 Falha no último nó disponível ({active_node.name}). Sem backup.")
                    raise e
        
        raise Exception("Falha em todos os nós após retentativas.")
