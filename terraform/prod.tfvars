# us-ashburn-1
region = "us-ashburn-1"

# Perfil padrao operacional: ARM pago em creditos usando A2.
# Mantem a instancia alinhada com o ambiente atual e evita depender da
# capacidade instavel do Always Free em A1.
instance_shape      = "VM.Standard.A2.Flex"
instance_ocpus      = 2
instance_memory_gbs = 12

# Regras de acesso
enable_ipv6 = false

# Rede
vcn_cidr    = "10.0.0.0/16"
subnet_cidr = "10.0.1.0/24"

# Availability Domain da tenancy atual.
availability_domain_name = "IgOd:US-ASHBURN-AD-1"
# ad_index_seed = "try-ad-2"

# Storage adicional (0 = nao cria)
extra_block_volume_size_gbs = 0

# Mantido em 200 GB para acompanhar a VM atual.
boot_volume_size_gbs = 200
