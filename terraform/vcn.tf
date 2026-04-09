# VCN (equivalente a VPC) para isolar a rede do DefiSys.
resource "oci_core_vcn" "defisys" {
  # CIDR simples e amplo para subnets futuras.
  compartment_id = local.compartment_id
  display_name   = "${local.project_name}-vcn"
  cidr_block     = var.vcn_cidr
}

# Internet Gateway para permitir acesso externo e updates do sistema.
resource "oci_core_internet_gateway" "defisys" {
  # Necessario para entrada/saida direta da subnet publica.
  compartment_id = local.compartment_id
  display_name   = "${local.project_name}-igw"
  vcn_id         = oci_core_vcn.defisys.id
  enabled        = true
}

# Tabela de rotas da subnet publica com saida para a internet.
resource "oci_core_route_table" "defisys_public" {
  # Sem NAT/Load Balancer para evitar custos: acesso direto pela VM.
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.defisys.id
  display_name   = "${local.project_name}-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.defisys.id
  }
}

# Subnet publica da VM do DefiSys.
resource "oci_core_subnet" "defisys_public" {
  # Subnet publica permite IP publico na VNIC da VM.
  compartment_id             = local.compartment_id
  vcn_id                     = oci_core_vcn.defisys.id
  display_name               = "${local.project_name}-public-subnet"
  cidr_block                 = var.subnet_cidr
  route_table_id             = oci_core_route_table.defisys_public.id
  security_list_ids          = [oci_core_security_list.defisys_public.id]
  dhcp_options_id            = oci_core_vcn.defisys.default_dhcp_options_id
  prohibit_public_ip_on_vnic = false
}
