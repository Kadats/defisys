# Perfil alternativo para consumir creditos do trial quando precisar de AMD64.
region = "us-ashburn-1"

instance_shape      = "VM.Standard.E5.Flex"
instance_ocpus      = 1
instance_memory_gbs = 6

enable_ipv6                 = false
vcn_cidr                    = "10.0.0.0/16"
subnet_cidr                 = "10.0.1.0/24"
availability_domain_name    = "IgOd:US-ASHBURN-AD-1"
extra_block_volume_size_gbs = 0
boot_volume_size_gbs        = 100
