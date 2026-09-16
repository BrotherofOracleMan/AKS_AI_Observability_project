variable "resource_group_name" {
  type        = string
  description = "Resource group for ACR + AKS"
  default     = "rg-terraform-ai-kubernetes"
}

variable "location" {
  type        = string
  description = "Azure region"
  default     = "eastus"
}

# Nit: ACR name was hard-coded; prefix + random_string avoids global name collisions
variable "acr_name_prefix" {
  type        = string
  description = "ACR name prefix (lowercase alphanumeric); random suffix appended for global uniqueness"
  default     = "aionk8sacr"
}

variable "aks_name" {
  type        = string
  description = "AKS cluster name"
  default     = "ai-on-kubernetes-aks"
}

variable "dns_prefix" {
  type        = string
  description = "DNS prefix for the AKS API server FQDN"
  default     = "aionk8s"
}

# Nit: overridable for lab cost (keep at 1)
variable "node_count" {
  type        = number
  description = "Default node pool size (use 1 for lab cost)"
  default     = 1
}

# Nit: overridable if Standard_B2s is unavailable in your region/quota
variable "vm_size" {
  type        = string
  description = "Node VM SKU (override if Standard_B2s unavailable in your region/quota)"
  default     = "Standard_B2s"
}
