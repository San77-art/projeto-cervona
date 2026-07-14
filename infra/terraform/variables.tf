variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project identifier used for resource naming"
  type        = string
  default     = "cernova"
}

variable "environment" {
  description = "Deployment environment (e.g. production, staging)"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type for the FastAPI app server"
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "cernova"
}

variable "db_username" {
  description = "Master username for the RDS instance"
  type        = string
  default     = "cernova_app"
}

variable "db_multi_az" {
  description = "Enable RDS Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "db_skip_final_snapshot" {
  description = "Skip final DB snapshot on destroy (set false for production)"
  type        = bool
  default     = true
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the app server (no default - must be set explicitly)"
  type        = string
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH access"
  type        = string
}

variable "anthropic_api_key" {
  description = "Anthropic API key used by the app for Claude extraction (stored in Secrets Manager, not written to state-visible defaults)"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "Signing key for internal JWT auth (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

# ---------------------------------------------------------------------------
# CI/CD (GitHub Actions -> ghcr.io -> EC2 via SSM)
# ---------------------------------------------------------------------------

variable "github_repository" {
  description = "GitHub repo allowed to assume the deploy role, as \"owner/repo\" (OIDC trust condition). Deploy is restricted to the main branch."
  type        = string
}

variable "ghcr_username" {
  description = "GitHub username/org whose GHCR package the EC2 instance pulls images from (stored in Secrets Manager, used for `docker login ghcr.io`)"
  type        = string
  sensitive   = true
}

variable "ghcr_pat" {
  description = "GitHub PAT with read:packages, used by the EC2 instance to pull the app image from ghcr.io (stored in Secrets Manager, not written to state-visible defaults)"
  type        = string
  sensitive   = true
}
