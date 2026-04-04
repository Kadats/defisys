# Guia de Contribuição - DefiSys

Este documento define os padrões e fluxos de trabalho para contribuir com o projeto DefiSys. Seguir estas regras garante que o ambiente de desenvolvimento (Poetry) e o ambiente de produção (Docker) permaneçam sincronizados e funcionais.

## 1. Fluxo de Trabalho Git (Git Flow)

Não comite diretamente na `main`. Utilize branches de feature/fix e Pull Requests.

### Padrão de Nomes de Branch
* **Features:** `feat/nome-da-feature` (ex: `feat/model-prediction-v1`)
* **Correções:** `fix/nome-do-bug` (ex: `fix/data-provider-merge`)
* **Tarefas:** `chore/nome-da-tarefa` (ex: `chore/repo-cleanup`)
* **Otimizações:** `tune/nome-da-otimizacao` (ex: `tune/strategy-ranges`)

### Fluxo de Merge
1.  Crie a branch a partir da `main` atualizada.
2.  Desenvolva e **teste** localmente.
3.  Abra um Pull Request (PR) para a `main`.
4.  Após aprovação/review, faça o Merge e delete a branch antiga.

---

## 2. Gerenciamento de Dependências (CRÍTICO)

Este projeto utiliza **Poetry** como fonte única de dependências do backend. O Docker também instala dependências a partir de `pyproject.toml` e `poetry.lock`.

### Como Adicionar uma Nova Biblioteca

**NUNCA** adicione dependências editando arquivos gerados manualmente.

1.  **Instale com Poetry:**
    ```bash
    poetry add nome-do-pacote
    ```
    *(Isso atualiza o `pyproject.toml` e o `poetry.lock`)*

2.  **Commit:** Adicione ambos os arquivos ao git:
    ```bash
    git add pyproject.toml poetry.lock
    ```

---

## 3. Testes e Qualidade

Antes de abrir um PR ou fazer um commit de feature, certifique-se de que nada foi quebrado.

### Rodar Testes Unitários
```bash
make test
```

### Rodar Testes na Stack Docker
```bash
make test-docker
```

### Subir a Stack e Validar em Um Comando
```bash
make up-test
```

### Verificações de Qualidade
```bash
make lint
make format
```
