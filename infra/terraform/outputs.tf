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

output "github_actions_deploy_role_arn" {
  description = "IAM role ARN for GitHub Actions to assume via OIDC - set this as the AWS_DEPLOY_ROLE_ARN repository variable"
  value       = aws_iam_role.github_actions_deploy.arn
}

output "ec2_name_tag" {
  description = "Name tag GitHub Actions filters on to find the app instance for deploy (aws ec2 describe-instances)"
  value       = "${local.name_prefix}-app"
}
