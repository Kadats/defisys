# Oracle Cloud: perfil operacional do DefiSys

Data de revisao: 2026-04-09

## Resumo objetivo

- O repositorio foi consolidado em um unico perfil operacional.
- A instancia padrao agora e `VM.Standard.A2.Flex` com `2 OCPUs`, `12 GB RAM` e `200 GB` de boot volume.
- Esse perfil usa creditos do `Free Trial` ou conta paga; nao depende do `Always Free`.
- A imagem permanece ARM (`aarch64`) para manter compatibilidade com o ambiente atual.

## Operacao

### Passo a passo basico

Entre na pasta do projeto:

```bash
cd /home/luckstyle/repo/private/defisys/terraform
```

Carregue as variaveis do arquivo `.env` na sua sessao atual do terminal:

```bash
set -a
source .env
set +a
```

Esse passo faz o Terraform enxergar automaticamente credenciais, OCIDs, caminho da chave SSH e demais configuracoes necessarias.

### Ver o que sera alterado (`terraform plan`)

Depois de carregar o `.env`, rode:

```bash
terraform plan
```

O `plan` nao cria nem remove nada. Ele apenas mostra o que o Terraform pretende fazer.

### Criar ou atualizar a infraestrutura (`terraform apply`)

Se o resultado do `plan` estiver correto, rode:

```bash
terraform apply
```

O Terraform vai mostrar o resumo e pedir confirmacao. Para continuar, digite:

```bash
yes
```

Depois disso ele cria ou atualiza a VM, rede e demais recursos gerenciados por este projeto.

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

Se voce quiser remover toda a infraestrutura gerenciada por este projeto, incluindo rede e VM, primeiro carregue o `.env`:

```bash
set -a
source .env
set +a
```

Depois rode:

```bash
terraform destroy
```

Assim como no `apply`, o Terraform vai pedir confirmacao antes de apagar os recursos.

## Nomenclatura

- O nome visivel da VM agora e `defisys`.
- Os `display_name` dos recursos OCI tambem foram alinhados para `defisys`.
- Os labels internos do Terraform tambem foram renomeados para `defisys`.
- Como os recursos ainda nao foram aplicados, nao ha necessidade de migracao de state.
