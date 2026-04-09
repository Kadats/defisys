# VM para hospedar os servicos do DefiSys.
resource "oci_core_instance" "defisys" {
  # O shape vem do tfvars para permitir alternar entre perfil ARM Always Free
  # e um fallback AMD64 pago com creditos.
  compartment_id      = local.compartment_id
  availability_domain = local.availability_domain_name
  display_name        = local.project_name
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gbs
  }

  create_vnic_details {
    # IP publico necessario para o apontamento DNS.
    subnet_id        = oci_core_subnet.defisys_public.id
    assign_public_ip = true
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
    # 100 GB consomem metade da cota Always Free de block storage.
    boot_volume_size_in_gbs = var.boot_volume_size_gbs
  }

  metadata = {
    # Chave SSH para acesso inicial (nao usa senha).
    ssh_authorized_keys = file(var.ssh_public_key_path)
  }
}

# Block volume opcional para dados persistentes (se habilitado).
resource "oci_core_volume" "defisys_data" {
  # Use apenas se precisar de mais espaco para dados do Postgres.
  count               = var.extra_block_volume_size_gbs > 0 ? 1 : 0
  compartment_id      = local.compartment_id
  availability_domain = local.availability_domain_name
  display_name        = "${local.project_name}-data"
  size_in_gbs         = var.extra_block_volume_size_gbs
}

# Anexar o block volume opcional na VM.
resource "oci_core_volume_attachment" "defisys_data" {
  # Anexado como paravirtualizado para melhor desempenho.
  count           = var.extra_block_volume_size_gbs > 0 ? 1 : 0
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.defisys.id
  volume_id       = oci_core_volume.defisys_data[0].id
}
