import hashlib
import hmac
import time
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SecurityAuditException(Exception):
    """Exceção lançada quando as permissões da chave de API violam a auditoria de segurança."""
    pass

class BinanceExchangeClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.binance.com", environment: str = "sandbox"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.environment = environment

    def _generate_signature(self, query_string: str) -> str:
        return hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def validate_api_permissions(self):
        """
        Consulta as permissões da API Key atual.
        Levanta SecurityAuditException se 'canWithdraw' for True (Risco Institucional).
        """
        # Em sandbox ou se as chaves estiverem vazias e o ambiente não for produção, ignoramos a verificação real
        if self.environment == "sandbox":
            logger.info("🛡️ [SANDBOX MODE] Ignorando validação real de permissões da API Key.")
            return

        if not self.api_key or not self.api_secret:
            if self.environment == "production":
                raise SecurityAuditException("Chaves de API ausentes em ambiente de PRODUÇÃO.")
            logger.warning("Chaves de API não configuradas. Verificação de segurança ignorada.")
            return

        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}"
        signature = self._generate_signature(query_string)
        url = f"{self.base_url}{endpoint}?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            # 401/403: Chave inválida
            if resp.status_code in [401, 403]:
                raise SecurityAuditException(f"API Key inválida ou sem permissões: {resp.status_code}")
            
            resp.raise_for_status()
            account_info = resp.json()
            
            # Auditoria Crítica: canWithdraw
            can_withdraw = account_info.get("canWithdraw", False)
            if can_withdraw:
                logger.critical("🚨 VIOLAÇÃO DE SEGURANÇA: Chave de API possui permissão de SAQUE (Withdraw).")
                raise SecurityAuditException("AUDITORIA FALHOU: A chave de API em produção DEVE ter saques bloqueados.")
            
            logger.info("✓ Auditoria de Segurança Passou: Saques estão bloqueados para esta API Key.")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao validar permissões da API Key: {str(e)}")
            if self.environment == "production":
                raise SecurityAuditException(f"Não foi possível validar permissões da API Key em Produção: {str(e)}")
