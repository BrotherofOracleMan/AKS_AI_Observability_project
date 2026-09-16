terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.25"
    }
    # Nit: random provider — append unique ACR name suffix (ACR names are globally unique)
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  required_version = ">= 1.1.0"
}

provider "azurerm" {
  features {}
}

# Nit: avoids "name already taken" on apply
resource "random_string" "acr_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# Azure Container Registry (name must be globally unique, alphanumeric only)
resource "azurerm_container_registry" "acr" {
  # Nit: prefix + random suffix instead of a hard-coded name
  name                = "${var.acr_name_prefix}${random_string.acr_suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  # Lab: admin user on for easy docker login; prefer az acr login / AcrPush later
  admin_enabled       = true
}

# AKS cluster (destroy when idle — node hours dominate cost)
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  dns_prefix          = var.dns_prefix

  default_node_pool {
    name = "default"
    # Nit: vars so you can shrink cost / swap SKU if B2s unavailable in region
    node_count = var.node_count
    vm_size    = var.vm_size
  }

  identity {
    type = "SystemAssigned"
  }
}

# AcrPull on kubelet identity (nodes pull images) — not cluster identity (control plane)
resource "azurerm_role_assignment" "aks_to_acr_pull" {
  scope                            = azurerm_container_registry.acr.id
  role_definition_name             = "AcrPull"
  # Nit: kubelet_identity uses object_id (cluster identity uses principal_id)
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}
