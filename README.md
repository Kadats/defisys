# DefiSys - Sistema de Provisão de Liquidez Automatizado

Este projeto é um sistema de trading automatizado projetado para atuar como um provedor de liquidez (LP) em pools DeFi de Bitcoin. A estratégia central visa otimizar os ganhos com taxas e a acumulação de ativos, utilizando uma combinação de indicadores técnicos e on-chain para gerenciar dinamicamente as posições.

## Estrutura de Pastas

- **/frontend**: (Em desenvolvimento) Interface de usuário para visualização de dados, gráficos e gerenciamento da estratégia.
- **/backend**: O núcleo do sistema, responsável pela coleta de dados, análise, backtesting e execução da estratégia.

## Configuração do Ambiente

Este projeto foi desenvolvido utilizando Python em um ambiente WSL (Ubuntu 24.04).

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git](https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git)
    cd DefiSys
    ```

2.  **Crie e Ative o Ambiente Virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as Dependências:**
    Use o Makefile para instalar as bibliotecas do arquivo `requirements.txt`.
    ```bash
    make install
    ```

## Como Executar

Com o ambiente virtual ativado, utilize o Makefile para rodar o sistema principal. O script irá coletar os dados mais recentes, executar o backtest com a estratégia atual e exibir os resultados.

```bash
make run

