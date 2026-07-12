output "ec2_public_ip" {
  description = "Public IP of the FastAPI app server"
  value       = aws_instance.app.public_ip
}

output "ec2_instance_id" {
  description = "Instance ID of the FastAPI app server"
  value       = aws_instance.app.id
}

output "rds_endpoint" {
  description = "RDS Postgres connection endpoint"
  value       = aws_db_instance.app.address
}

output "s3_bucket_name" {
  description = "Name of the app storage bucket"
  value       = aws_s3_bucket.app.bucket
}

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret holding DB credentials"
  value       = aws_secretsmanager_secret.db.arn
}

output "app_secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret holding app secrets (Anthropic API key, JWT key)"
  value       = aws_secretsmanager_secret.app.arn
}
