#!/bin/bash
set -e

echo "🚀 Iniciando Setup Cloud para DefiSys..."

# 1. Instalação de Dependências de Sistema
echo "📦 Instalando Docker e ferramentas essenciais..."
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git

# Instalar Docker se não existir
if ! command -v docker &> /dev/null; then
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# 2. Configuração de Variáveis de Ambiente
if [ ! -f .env ]; then
    echo "📄 Criando arquivo .env a partir do template..."
    cp .env.example .env
    echo "⚠️  ATENÇÃO: Edite o arquivo .env com suas chaves reais antes de rodar o sistema!"
fi

# 3. Preparação de Volumes e Permissões
echo "📂 Preparando estrutura de logs..."
mkdir -p backend/logs
chmod 777 backend/logs

# 4. Inicialização do Sistema
echo "🏗️  Construindo e iniciando contêineres..."
sudo docker compose up --build -d

echo "✅ Setup concluído!"
echo "Acompanhe os logs com: sudo docker compose logs -f backend"
