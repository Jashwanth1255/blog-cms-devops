# Terraform: provisions the Blog CMS stack as Docker containers on your machine.
# Uses the Docker provider, so no cloud account is needed.
#   terraform init
#   terraform plan
#   terraform apply
#   terraform destroy

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  # Windows (Docker Desktop): uncomment the next line
  # host = "npipe:////.//pipe//docker_engine"
}

# ---------- Network ----------
resource "docker_network" "blog" {
  name = "${var.project_name}-net"
}

# ---------- PostgreSQL ----------
resource "docker_image" "postgres" {
  name         = "postgres:16-alpine"
  keep_locally = true
}

resource "docker_volume" "pgdata" {
  name = "${var.project_name}-pgdata"
}

resource "docker_container" "db" {
  name  = "${var.project_name}-db"
  image = docker_image.postgres.image_id

  env = [
    "POSTGRES_DB=${var.db_name}",
    "POSTGRES_USER=${var.db_user}",
    "POSTGRES_PASSWORD=${var.db_password}",
  ]

  networks_advanced {
    name    = docker_network.blog.name
    aliases = ["db"]
  }

  volumes {
    volume_name    = docker_volume.pgdata.name
    container_path = "/var/lib/postgresql/data"
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.db_user} -d ${var.db_name}"]
    interval = "5s"
    timeout  = "3s"
    retries  = 10
  }
}

# ---------- Blog API (built from ../app) ----------
resource "docker_image" "api" {
  name = "blog-cms-api:tf"
  build {
    context = "${path.module}/../app"
  }
  triggers = {
    code_hash = filesha1("${path.module}/../app/app.py")
  }
}

resource "docker_container" "api" {
  name    = "${var.project_name}-api"
  image   = docker_image.api.image_id
  restart = "unless-stopped"

  env = [
    "DATABASE_URL=postgresql://${var.db_user}:${var.db_password}@db:5432/${var.db_name}",
    "APP_VERSION=${var.app_version}",
  ]

  ports {
    internal = 5000
    external = var.api_port
  }

  networks_advanced {
    name = docker_network.blog.name
  }

  depends_on = [docker_container.db]
}
