output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "ACR login server — use for docker tag/push and Deployment image"
}

output "acr_name" {
  value       = azurerm_container_registry.acr.name
  description = "name of azure container registry"
}

output "aks_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "AKS cluster name"
}

output "aks_resource_group_name" {
  value       = azurerm_kubernetes_cluster.aks.resource_group_name
  description = "Resource group of the AKS cluster (for az aks get-credentials)"
}

# Nit: dropped aks_kube_config output — use:
#   az aks get-credentials --resource-group <rg> --name <aks_name>

output "workload_identity_client_id" {
  value       = azurerm_user_assigned_identity.aks_project_identity.client_id
  description = "Client ID for the ai-proxy ServiceAccount annotation"
}