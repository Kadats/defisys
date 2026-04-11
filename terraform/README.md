# Oracle Cloud: perfil operacional do DefiSys

Data de revisao: 2026-04-09

## Resumo objetivo

- O repositorio foi consolidado em um unico perfil operacional.
- A instancia padrao agora e `VM.Standard.A2.Flex` com `2 OCPUs`, `12 GB RAM` e `200 GB` de boot volume.
- Esse perfil usa creditos do `Free Trial` ou conta paga; nao depende do `Always Free`.
- A imagem permanece ARM (`aarch64`) para manter compatibilidade com o ambiente atual.

## Operacao

### Aplicar a infraestrutura

Carregue as variaveis do `.env` e aplique:

```bash
set -a
source .env
set +a
terraform apply
```

Para revisar antes:

```bash
terraform plan
```

### Acessar a VM por SSH

Depois do `apply`, obtenha o IP publico:

```bash
terraform output instance_public_ip
```

Acesse com a chave privada correspondente a publica informada em `TF_VAR_ssh_public_key_path`.
Para Ubuntu, o usuario padrao e `ubuntu`:

```bash
ssh -i /caminho/da/chave_privada ubuntu@SEU_IP
```

Exemplo:

```bash
ssh -i ~/.ssh/id_rsa ubuntu@203.0.113.10
```

Observacao: a porta `22` so aceita os CIDRs configurados em `TF_VAR_allowed_ssh_cidr`.

### Destruir os recursos

Para destruir toda a infraestrutura gerenciada por este estado, incluindo rede e VM:

```bash
set -a
source .env
set +a
terraform destroy
```

## Nomenclatura

- O nome visivel da VM agora e `defisys`.
- Os `display_name` dos recursos OCI tambem foram alinhados para `defisys`.
- Os labels internos do Terraform tambem foram renomeados para `defisys`.
- Como os recursos ainda nao foram aplicados, nao ha necessidade de migracao de state.
