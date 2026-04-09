output "instance_public_ip" {
  description = "IP publico da VM do DefiSys."
  value       = data.oci_core_vnic.defisys_primary.public_ip_address
}

output "instance_id" {
  description = "OCID da VM."
  value       = oci_core_instance.defisys.id
}

output "vcn_id" {
  description = "OCID da VCN."
  value       = oci_core_vcn.defisys.id
}

output "subnet_id" {
  description = "OCID da subnet publica."
  value       = oci_core_subnet.defisys_public.id
}

output "compartment_id" {
  description = "OCID do compartment usado."
  value       = local.compartment_id
}
