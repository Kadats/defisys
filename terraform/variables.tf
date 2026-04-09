variable "tenancy_ocid" {
  description = "OCI tenancy OCID (equivalente ao AWS Account ID)."
  type        = string
}

variable "user_ocid" {
  description = "OCI user OCID usado pelo Terraform."
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint da API key do usuario OCI."
  type        = string
}

variable "private_key_path" {
  description = "Caminho local para a chave privada da API key da OCI."
  type        = string
}

variable "region" {
  description = "Regiao OCI (ex: sa-saopaulo-1)."
  type        = string
}

variable "compartment_ocid" {
  description = "OCID do compartment existente. Se vazio e create_compartment=true, sera criado um compartment novo."
  type        = string
  default     = ""
}

variable "create_compartment" {
  description = "Quando true, cria um compartment novo para o DefiSys."
  type        = bool
  default     = false
}

variable "ssh_public_key_path" {
  description = "Caminho para a chave publica SSH (.pub) para acesso a VM."
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "Seu IP fixo em formato CIDR /32 (ex: 203.0.113.10/32)."
  type        = string
}

variable "enable_ipv6" {
  description = "Habilita regras IPv6 (so use se sua VCN e instance tiverem IPv6)."
  type        = bool
  default     = false
}

variable "instance_shape" {
  description = "Shape flex da VM. Padrao recomendado: VM.Standard.A1.Flex."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  description = "OCPUs da VM. Em shapes x86 flex, 1 OCPU equivale a 2 vCPUs."
  type        = number
  default     = 2
}

variable "instance_memory_gbs" {
  description = "Memoria da VM em GB para shapes flex."
  type        = number
  default     = 12
}

variable "vcn_cidr" {
  description = "CIDR da VCN."
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR da subnet publica."
  type        = string
  default     = "10.0.1.0/24"
}

variable "availability_domain_name" {
  description = "Nome do Availability Domain. Se vazio, sera escolhido automaticamente."
  type        = string
  default     = ""
}

variable "ad_index_seed" {
  description = "Seed para escolher automaticamente outro AD quando necessario."
  type        = string
  default     = "default"
}

variable "boot_volume_size_gbs" {
  description = "Tamanho do boot volume (GB) da VM."
  type        = number
  default     = 100
}

variable "extra_block_volume_size_gbs" {
  description = "Tamanho do block volume adicional (0 para nao criar)."
  type        = number
  default     = 0
}
