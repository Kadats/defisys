locals {
  project_name = "defisys"

  # Escolhe o compartment final: criado ou fornecido via variavel.
  compartment_id = var.create_compartment ? oci_identity_compartment.defisys[0].id : var.compartment_ocid

  # Escolhe o Availability Domain: manual ou automatico (random).
  availability_domain_name = var.availability_domain_name != "" ? var.availability_domain_name : data.oci_identity_availability_domains.ads.availability_domains[random_integer.ad_index.result].name
}
