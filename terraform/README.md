# Oracle Cloud: perfis recomendados para o DefiSys

Data de revisao: 2026-04-09

## Resumo objetivo

- A Oracle continua oferecendo `Free Trial` por 30 dias com `US$ 300` em creditos.
- O perfil padrao do projeto agora usa `Arm` porque o codigo e o stack Docker estao compativeis com `aarch64`.
- O melhor custo-beneficio para manter quase tudo em `Always Free` e `VM.Standard.A1.Flex`.
- Em OCI x86, `1 OCPU = 2 vCPUs`; por isso um host `amd64` pequeno e util geralmente cai fora do `Always Free`.

## Limites relevantes do Always Free

- `AMD64`: ate `2` instancias `VM.Standard.E2.1.Micro`, cada uma fixa em `1 OCPU` e `1 GB RAM`.
- `Arm`: ate `4 OCPUs` e `24 GB RAM` somados em `VM.Standard.A1.Flex`.
- `Block Volume`: `200 GB` totais somando boot volumes e block volumes.
- Rede publica direta: `80/443` abertos para a internet e `22` restrito ao seu `allowed_ssh_cidr`.

## Perfis incluidos neste diretorio

### `prod.tfvars`

Perfil padrao recomendado:

- `VM.Standard.A1.Flex`
- `2 OCPUs`
- `12 GB RAM`
- `100 GB` de boot volume

Uso:

```bash
terraform plan -var-file=prod.tfvars
```

Observacao: este perfil fica dentro do `Always Free` e deixa metade da cota de block storage ainda livre.

### `credit-amd64.tfvars`

Perfil alternativo para consumir creditos do `Free Trial` quando voce precisar de `amd64`:

- `VM.Standard.E5.Flex`
- `1 OCPU` (`2 vCPUs`)
- `6 GB RAM`
- `100 GB` de boot volume

Uso:

```bash
terraform plan -var-file=credit-amd64.tfvars
```

Observacao: este perfil sai do `Always Free` de compute e deve usar os creditos do trial ou `Pay As You Go`.

## Nomenclatura

- O nome visivel da VM agora e `defisys`.
- Os `display_name` dos recursos OCI tambem foram alinhados para `defisys`.
- Os labels internos do Terraform tambem foram renomeados para `defisys`.
- Como os recursos ainda nao foram aplicados, nao ha necessidade de migracao de state.
