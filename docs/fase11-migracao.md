# Fase 11: Plano de Migração e Estabilização

## 1. Checklist de Portas (Oracle Cloud Console)
Verifique se a **Security List** (ou Network Security Group) associada à Subnet (VCN) da VPS possui regras de Ingress permitindo tráfego TCP para as seguintes portas a partir da internet (`0.0.0.0/0` ou dos IPs específicos permitidos):
- **3000:** Frontend (Interface do Usuário)
- **8000:** Backend (API e WebSockets)
- **22:** SSH (Certifique-se de que está restrito aos IPs autorizados para evitar ataques)
- *(Opcional)* **80/443:** Caso futuramente configure um proxy reverso como Nginx/Caddy.

## 2. Comandos Ubuntu (Firewall iptables)
A imagem Ubuntu da Oracle Cloud possui regras predefinidas no iptables que bloqueiam tráfego de entrada. Execute os comandos abaixo via SSH para liberar as portas 3000 e 8000. Inserir na linha 6 geralmente garante que a regra venha antes do bloqueio padrão (`REJECT`), mantendo o acesso SSH intacto.

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

## 3. Configuração de DNS (Rede Docker)
Para corrigir o problema de Egress do container do backend (que não consegue resolver nomes externos por conflitos com o `systemd-resolved` do Ubuntu), adicione a configuração de DNS explícita no `docker-compose.yml`.

Adicione a chave `dns` nos serviços `backend` e `postgres`:
```yaml
services:
  backend:
    # ...
    dns:
      - 8.8.8.8
      - 1.1.1.1
    # ...

  postgres:
    # ...
    dns:
      - 8.8.8.8
      - 1.1.1.1
    # ...
```

## 4. Variáveis de Ambiente (.env na VPS e Código)
Para que o sistema seja acessível externamente, as referências a `localhost` precisam ser atualizadas para o **IP Público da VPS**:

- **No Frontend (.env ou variáveis na VPS):** A variável que indica onde a API está sendo exposta no navegador deve apontar para o IP da VPS.
- **No Backend (`backend/src/api.py`):** O middleware de CORS deve ser atualizado para permitir a origem pública. Adicionar:
  ```python
  "http://<IP_PUBLICO_VPS>:3000",
  "https://<IP_PUBLICO_VPS>:3000"
  ```
  Ou, provisoriamente, usar `allow_origins=["*"]` durante os testes iniciais de migração.

## 5. Mapeamento de Volumes (Bind Mounts)
Para garantir persistência segura e facilitar os backups na VPS, altere o mapeamento de volumes no `docker-compose.yml` para usar pastas locais (`./postgres_data`).

Exemplo no serviço `postgres`:
```yaml
    volumes:
      - ./postgres_data/producao:/var/lib/postgresql/data
```
Exemplo no `postgres_test`:
```yaml
    volumes:
      - ./postgres_data/teste:/var/lib/postgresql/data
```
Exemplo no `postgres_paper`:
```yaml
    volumes:
      - ./postgres_data/paper:/var/lib/postgresql/data
```
*(Lembre-se de remover a seção `volumes:` vazia no final do arquivo referente aos named volumes antigos se não forem mais usados).*