# us-ashburn-1
region = "us-ashburn-1"

# Perfil padrao: ARM em Always Free.
# Free Trial OCI: 30 dias + US$ 300 em creditos.
# Always Free relevante:
# - Arm: ate 4 OCPUs / 24 GB somados em VM.Standard.A1.Flex
# - Block Volume: 200 GB totais
# Este perfil fica confortavel dentro do Always Free e entrega mais folga do que
# o minimo pedido originalmente.
instance_shape      = "VM.Standard.A1.Flex"
instance_ocpus      = 2
instance_memory_gbs = 12

# Regras de acesso
enable_ipv6 = false

# Rede
vcn_cidr    = "10.0.0.0/16"
subnet_cidr = "10.0.1.0/24"

# Availability Domain (opcional) vLCq:US-ASHBURN-AD-1 vLCq:US-ASHBURN-AD-2 vLCq:US-ASHBURN-AD-3
availability_domain_name = "vLCq:US-ASHBURN-AD-1"
# ad_index_seed = "try-ad-2"

# Storage adicional (0 = nao cria)
extra_block_volume_size_gbs = 0

# 100 GB ocupam metade da cota Always Free total de block storage.
boot_volume_size_gbs = 100
