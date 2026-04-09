import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from backend.src.core.rpc_manager import RPCManager

def test_rpc_manager_failover():
    """TDD: Simula falha no primário e fallback para secundário."""
    async def run_test():
        # Simulando 3 RPCs
        primary_url = "http://primary.rpc"
        secondary_url = "http://secondary.rpc"
        decentralized_url = "http://decentralized.rpc"
        
        manager = RPCManager(
            primary_url=primary_url,
            secondary_url=secondary_url,
            decentralized_url=decentralized_url
        )
        
        # Mock do _make_request (método interno de transporte)
        async def mock_make_request(url, payload):
            if url == primary_url:
                raise asyncio.TimeoutError("Timeout no primário")
            elif url == secondary_url:
                return {"jsonrpc": "2.0", "id": 1, "result": "0x100"} # Saldo em hex
            return None

        with patch.object(manager, '_make_request', side_effect=mock_make_request):
            # Chama um método qualquer
            result = await manager.call("eth_getBalance", ["0x123", "latest"])
            
            # O resultado deve ser o do secundário
            assert result == "0x100"
            # O nó ativo agora deve ser o secundário
            assert manager.get_active_rpc().url == secondary_url
            
    asyncio.run(run_test())

def test_rpc_manager_health_check_on_start():
    """TDD: Valida se o Health Check marca nós offline corretamente."""
    async def run_test():
        primary_url = "http://primary.rpc"
        secondary_url = "http://secondary.rpc"
        decentralized_url = "http://decentralized.rpc"

        manager = RPCManager(
            primary_url=primary_url,
            secondary_url=secondary_url,
            decentralized_url=decentralized_url
        )

        async def mock_make_request(url, payload):
            if url == primary_url:
                raise Exception("Offline")
            return {"jsonrpc": "2.0", "id": 1, "result": "0x1"} # Online

        with patch.object(manager, '_make_request', side_effect=mock_make_request):
            await manager.perform_health_check()
            
            # O primeiro nó deve estar down
            assert manager.nodes[0].is_healthy is False
            assert manager.nodes[1].is_healthy is True
            # Ativo deve ser o primeiro saudável (o secundário)
            assert manager.get_active_rpc().url == secondary_url

    asyncio.run(run_test())
