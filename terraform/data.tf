# Lista de Availability Domains para escolher onde criar a VM.
data "oci_identity_availability_domains" "ads" {
  # Usamos o primeiro AD disponivel para simplicidade.
  compartment_id = var.tenancy_ocid
}

# Escolhe um AD automaticamente (random), mas permite override manual.
resource "random_integer" "ad_index" {
  min = 0
  max = length(data.oci_identity_availability_domains.ads.availability_domains) - 1

  keepers = {
    seed = var.ad_index_seed
  }
}

# Imagem oficial Ubuntu 24.04 compativel com o shape escolhido.
data "oci_core_images" "ubuntu" {
  # Pega a imagem mais recente para o shape definido.
  compartment_id           = var.tenancy_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# Descobrir a VNIC primaria para obter o IP publico.
data "oci_core_vnic_attachments" "defisys" {
  # Necessario para buscar o IP publico apos criar a VM.
  compartment_id = local.compartment_id
  instance_id    = oci_core_instance.defisys.id
}

# VNIC primaria usada nos outputs.
data "oci_core_vnic" "defisys_primary" {
  # O IP publico sai daqui e vai para o DNS.
  vnic_id = data.oci_core_vnic_attachments.defisys.vnic_attachments[0].vnic_id
}
