import unittest
from unittest.mock import patch, MagicMock
import os
from backend.src.core.exchange import BinanceExchangeClient, SecurityAuditException
from backend.src.core.trading_engine import TradingEngine

class RedTeamSecurityTest(unittest.TestCase):
    
    def test_full_permission_api_key_blocks_execution(self):
        """
        RED TEAM: Tenta rodar o sistema com uma chave que tem permissão de saque.
        O sistema deve recusar o boot em modo produção.
        """
        # Mock das chaves de API
        api_key = "fake_key"
        api_secret = "fake_secret"
        
        # Mock da resposta da Binance com canWithdraw=True (Vulnerabilidade)
        mock_account_info = {
            "canWithdraw": True,
            "canDeposit": True,
            "canTrade": True
        }
        
        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_account_info
            mock_get.return_value = mock_resp
            
            # Forçamos modo produção no cliente e as chaves
            client = BinanceExchangeClient(api_key, api_secret, environment="production")
            
            print("\n[RED TEAM] Testando chave com permissão de SAQUE...")
            with self.assertRaises(SecurityAuditException) as cm:
                client.validate_api_permissions()
            
            print(f"[PASSED] Bloqueio confirmado: {cm.exception}")

    def test_missing_keys_in_production_blocks_execution(self):
        """
        RED TEAM: Tenta rodar produção sem chaves configuradas.
        """
        # Precisamos mockar _settings no config.py
        with patch('backend.src.config._settings') as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.BINANCE_API_KEY = ""
            mock_settings.BINANCE_API_SECRET = ""
            mock_settings.PROJECT_ROOT = "/app"
            
            from backend.src.config import validate_production_secrets
            
            print("[RED TEAM] Testando produção sem chaves...")
            with self.assertRaises(RuntimeError) as cm:
                validate_production_secrets()
            
            print(f"[PASSED] Bloqueio confirmado: {cm.exception}")

if __name__ == "__main__":
    unittest.main()
