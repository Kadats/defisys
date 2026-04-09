provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

check "compartment_configuration" {
  assert {
    condition     = var.create_compartment || trimspace(var.compartment_ocid) != ""
    error_message = "Defina compartment_ocid com um OCID valido ou use create_compartment=true para o Terraform criar o compartment do DefiSys."
  }
}

resource "oci_identity_compartment" "defisys" {
  # Compartment dedicado para isolar os recursos do DefiSys dentro da tenancy.
  count          = var.create_compartment ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = local.project_name
  description    = "Compartment do DefiSys com foco em ganhar dineiro com DeFi na OCI. Criado por Terraform."
  enable_delete  = false
}
