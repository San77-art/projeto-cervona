terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# Networking (default VPC / subnets)
# ---------------------------------------------------------------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ---------------------------------------------------------------------------
# Security groups
# ---------------------------------------------------------------------------

resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-app"
  description = "FastAPI app server"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "FastAPI"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.name_prefix}-app" })
}

resource "aws_security_group" "db" {
  name        = "${local.name_prefix}-db"
  description = "RDS Postgres - access from app servers only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.name_prefix}-db" })
}

# ---------------------------------------------------------------------------
# S3 bucket (app storage: uploads, XML files, etc.)
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "app" {
  bucket = "${local.name_prefix}-storage-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# RDS Postgres
# ---------------------------------------------------------------------------

resource "random_password" "db" {
  length  = 24
  special = false
}

resource "aws_db_subnet_group" "app" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = data.aws_subnets.default.ids
  tags       = local.tags
}

resource "aws_db_instance" "app" {
  identifier     = "${local.name_prefix}-db"
  engine         = "postgres"
  engine_version = "16.3"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.app.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  backup_retention_period = 7
  skip_final_snapshot     = var.db_skip_final_snapshot
  deletion_protection     = var.environment == "production"

  tags = local.tags
}

# ---------------------------------------------------------------------------
# Secrets Manager - DB credentials
# ---------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "db" {
  name = "${local.name_prefix}/db-credentials"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    host     = aws_db_instance.app.address
    port     = aws_db_instance.app.port
    dbname   = var.db_name
  })
}

# ---------------------------------------------------------------------------
# Secrets Manager - app secrets (Anthropic API key, JWT signing key)
# ---------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "app" {
  name = "${local.name_prefix}/app-secrets"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    anthropic_api_key = var.anthropic_api_key
    jwt_secret_key    = var.jwt_secret_key
  })
}

# ---------------------------------------------------------------------------
# Secrets Manager - ghcr.io pull credentials
#
# Kept out of aws_secretsmanager_secret.app on purpose: that secret is dumped
# wholesale into /etc/cernova-app.env, which is passed to the app container
# via `docker run --env-file` — the pull PAT has no business being injected
# into the app process. This one is only read by the deploy script.
# ---------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "ghcr" {
  name = "${local.name_prefix}/ghcr-credentials"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "ghcr" {
  secret_id = aws_secretsmanager_secret.ghcr.id
  secret_string = jsonencode({
    ghcr_username = var.ghcr_username
    ghcr_pat      = var.ghcr_pat
  })
}

# ---------------------------------------------------------------------------
# IAM role for the EC2 app server
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${local.name_prefix}-app-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "app" {
  statement {
    sid     = "SecretsManagerRead"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.db.arn,
      aws_secretsmanager_secret.app.arn,
      aws_secretsmanager_secret.ghcr.arn,
    ]
  }

  statement {
    sid = "S3AppBucket"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.app.arn,
      "${aws_s3_bucket.app.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "${local.name_prefix}-app-policy"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}

# Lets the SSM Agent (pre-installed on the AL2023 AMI) register the instance
# as a managed node, so GitHub Actions can run the deploy script via
# ssm:SendCommand instead of opening SSH to the runners' IPs.
resource "aws_iam_role_policy_attachment" "app_ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name = "${local.name_prefix}-app-profile"
  role = aws_iam_role.app.name
}

# ---------------------------------------------------------------------------
# GitHub Actions OIDC -> IAM role, for deploying via SSM without static AWS keys
# ---------------------------------------------------------------------------

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
  tags            = local.tags
}

data "aws_iam_policy_document" "github_actions_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Restrict to pushes/merges on main - deploy should not run off any branch.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = "${local.name_prefix}-gha-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "github_actions_deploy" {
  statement {
    sid       = "DescribeInstances"
    actions   = ["ec2:DescribeInstances"]
    resources = ["*"] # DescribeInstances does not support resource-level restriction
  }

  statement {
    sid       = "SendDeployCommand"
    actions   = ["ssm:SendCommand"]
    resources = [aws_instance.app.arn]
  }

  statement {
    sid       = "SendCommandDocument"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript"]
  }

  statement {
    sid       = "ReadCommandResult"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
    resources = ["*"] # these calls take a command ID, not an instance/document ARN
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "${local.name_prefix}-gha-deploy-policy"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}

# ---------------------------------------------------------------------------
# EC2 app server
# ---------------------------------------------------------------------------

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  key_name               = var.key_name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  # NOTE on indentation: the outer closing EOF and the inner closing SCRIPT
  # must both sit at column 0 (verified against actual `terraform apply`
  # output, not just docs) - Terraform's <<- heredoc strips leading
  # whitespace equal to the CLOSING marker's own indentation from every
  # line, uniformly. If EOF here were indented, that same amount would get
  # stripped from "#!/bin/bash" too, leaving it non-flush-left - which
  # cloud-init requires to recognize this as a shell script at all - and
  # would similarly break plain bash's own exact-match rule for the inner
  # SCRIPT terminator.
  user_data = <<-EOF
#!/bin/bash
    set -euo pipefail
    dnf update -y
    dnf install -y python3.11 python3.11-pip git jq docker

    systemctl enable --now docker

    # Fetch app secrets from Secrets Manager and drop them into the app env file
    # (this becomes the --env-file for the app container - see deploy script below).
    aws secretsmanager get-secret-value \
      --region ${var.aws_region} \
      --secret-id ${aws_secretsmanager_secret.app.name} \
      --query SecretString --output text | jq -r \
      'to_entries[] | "\(.key | ascii_upcase)=\(.value)"' > /etc/cernova-app.env

    aws secretsmanager get-secret-value \
      --region ${var.aws_region} \
      --secret-id ${aws_secretsmanager_secret.db.name} \
      --query SecretString --output text | jq -r \
      '"DATABASE_URL=postgresql://\(.username):\(.password)@\(.host):\(.port)/\(.dbname)"' >> /etc/cernova-app.env

    chmod 600 /etc/cernova-app.env

    # ghcr.io pull credentials, kept separate from /etc/cernova-app.env on
    # purpose - only the deploy script's `docker login` needs these, the app
    # container itself never should.
    aws secretsmanager get-secret-value \
      --region ${var.aws_region} \
      --secret-id ${aws_secretsmanager_secret.ghcr.name} \
      --query SecretString --output text | jq -r \
      'to_entries[] | "\(.key | ascii_upcase)=\(.value)"' > /etc/cernova-ghcr.env

    chmod 600 /etc/cernova-ghcr.env

    # Deploy script - invoked by GitHub Actions over SSM Run Command
    # (aws ssm send-command) on every push to main, passing the image ref as $1.
    cat > /usr/local/bin/cernova-deploy.sh <<'SCRIPT'
#!/bin/bash
    set -euo pipefail
    IMAGE="$${1:?usage: cernova-deploy.sh <image>}"

    set -a
    source /etc/cernova-ghcr.env
    set +a

    echo "$GHCR_PAT" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
    docker pull "$IMAGE"

    docker stop cernova-api >/dev/null 2>&1 || true
    docker rm cernova-api >/dev/null 2>&1 || true

    docker run -d \
      --name cernova-api \
      --restart unless-stopped \
      --env-file /etc/cernova-app.env \
      -p 8000:8000 \
      "$IMAGE"

    for i in $(seq 1 10); do
      if curl -sf http://localhost:8000/api/v1/health >/dev/null; then
        echo "cernova-api is healthy"
        docker image prune -af --filter "until=24h" >/dev/null 2>&1 || true
        exit 0
      fi
      sleep 3
    done

    echo "cernova-api failed its health check after deploy" >&2
    docker logs --tail 100 cernova-api >&2 || true
    exit 1
SCRIPT

    chmod 755 /usr/local/bin/cernova-deploy.sh
EOF

  tags = merge(local.tags, { Name = "${local.name_prefix}-app" })
}
