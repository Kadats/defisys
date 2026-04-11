# Perfil ARM pago mais novo para usar creditos fora do Always Free.
# Baseado em OCI Ampere A2, mais recente que A1 e com melhor performance por OCPU.
# Mantem memoria semelhante ao perfil padrao atual, com menor consumo de OCPUs.
region = "us-ashburn-1"

instance_shape      = "VM.Standard.A2.Flex"
instance_ocpus      = 2
instance_memory_gbs = 12

enable_ipv6 = false

vcn_cidr    = "10.0.0.0/16"
subnet_cidr = "10.0.1.0/24"

# Mantido explicito com o prefixo valido da tenancy.
availability_domain_name = "IgOd:US-ASHBURN-AD-1"

extra_block_volume_size_gbs = 0
boot_volume_size_gbs        = 200
