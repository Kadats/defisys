# Security List para restringir SSH e liberar 80/443 diretamente para a internet.
resource "oci_core_security_list" "defisys_public" {
  # Security List aplica regras na subnet (modelo simples para 1 VM).
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.defisys.id
  display_name   = "${local.project_name}-public-sl"

  egress_security_rules {
    # Egress livre para updates do sistema e downloads da aplicacao.
    protocol         = "all"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
  }

  dynamic "egress_security_rules" {
    for_each = var.enable_ipv6 ? [1] : []
    content {
      protocol         = "all"
      destination      = "::/0"
      destination_type = "CIDR_BLOCK"
    }
  }

  dynamic "ingress_security_rules" {
    # SSH somente dos CIDRs explicitamente permitidos.
    for_each = toset([
      for cidr in split(",", var.allowed_ssh_cidr) : trimspace(cidr)
      if trimspace(cidr) != ""
    ])
    content {
      protocol    = "6"
      source      = ingress_security_rules.value
      source_type = "CIDR_BLOCK"
      tcp_options {
        min = 22
        max = 22
      }
    }
  }

  dynamic "ingress_security_rules" {
    # Portas operacionais atuais do projeto acessiveis apenas dos CIDRs permitidos.
    for_each = {
      for pair in setproduct(
        toset([
          for cidr in split(",", var.allowed_ssh_cidr) : trimspace(cidr)
          if trimspace(cidr) != ""
        ]),
        toset([5173, 8000, 5432, 5433, 5434, 3000])
      ) :
      "${pair[0]}:${pair[1]}" => {
        cidr = pair[0]
        port = pair[1]
      }
    }
    content {
      protocol    = "6"
      source      = ingress_security_rules.value.cidr
      source_type = "CIDR_BLOCK"
      tcp_options {
        min = ingress_security_rules.value.port
        max = ingress_security_rules.value.port
      }
    }
  }

  # ingress_security_rules {
  #   # HTTP publico direto.
  #   protocol    = "6"
  #   source      = "0.0.0.0/0"
  #   source_type = "CIDR_BLOCK"
  #   tcp_options {
  #     min = 80
  #     max = 80
  #   }
  # }

  # ingress_security_rules {
  #   # HTTPS publico direto.
  #   protocol    = "6"
  #   source      = "0.0.0.0/0"
  #   source_type = "CIDR_BLOCK"
  #   tcp_options {
  #     min = 443
  #     max = 443
  #   }
  # }

  dynamic "ingress_security_rules" {
    # IPv6 HTTP publico (opcional) se sua conta/VCN suportar IPv6.
    for_each = var.enable_ipv6 ? [1] : []
    content {
      protocol    = "6"
      source      = "::/0"
      source_type = "CIDR_BLOCK"
      tcp_options {
        min = 80
        max = 80
      }
    }
  }

  dynamic "ingress_security_rules" {
    # IPv6 HTTPS publico (opcional) se sua conta/VCN suportar IPv6.
    for_each = var.enable_ipv6 ? [1] : []
    content {
      protocol    = "6"
      source      = "::/0"
      source_type = "CIDR_BLOCK"
      tcp_options {
        min = 443
        max = 443
      }
    }
  }
}
