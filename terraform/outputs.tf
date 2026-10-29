output "api_url" {
  description = "Open this in Postman or a browser"
  value       = "http://localhost:${var.api_port}"
}

output "containers" {
  value = [docker_container.db.name, docker_container.api.name]
}
