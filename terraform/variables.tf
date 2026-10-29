variable "project_name" {
  description = "Prefix for every resource name"
  type        = string
  default     = "tf-blog"
}

variable "api_port" {
  description = "Port on your machine for the API (5001 so it doesn't clash with Docker Compose on 5000)"
  type        = number
  default     = 5001
}

variable "app_version" {
  type    = string
  default = "1.0.0"
}

variable "db_name" {
  type    = string
  default = "blogdb"
}

variable "db_user" {
  type    = string
  default = "bloguser"
}

variable "db_password" {
  type      = string
  default   = "blogpass"
  sensitive = true
}
