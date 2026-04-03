# ──────────────────────────────────────────────────────────────────────
# bh-audit-events DynamoDB table + IAM policy
#
# Production-ready configuration:
#   - PAY_PER_REQUEST (on-demand) billing
#   - Server-side encryption (AWS-owned key by default)
#   - Point-in-time recovery enabled
#   - TTL on the `ttl` attribute for automatic 6-year expiration
#   - 3 GSIs matching the bh-fastapi-audit DynamoDBSink schema
#   - Minimal IAM policy for the application role
#
# Usage:
#   cd terraform
#   terraform init
#   terraform plan -var="environment=prod"
#   terraform apply -var="environment=prod"
# ──────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# ──────────────────────────────────────────────────────────────────────
# Variables
# ──────────────────────────────────────────────────────────────────────

variable "region" {
  description = "AWS region for the DynamoDB table"
  type        = string
  default     = "us-east-1"
}

variable "table_name" {
  description = "DynamoDB table name"
  type        = string
  default     = "bh_audit_events"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "ttl_enabled" {
  description = "Enable TTL-based automatic item deletion"
  type        = bool
  default     = true
}

variable "point_in_time_recovery" {
  description = "Enable point-in-time recovery (recommended for prod)"
  type        = bool
  default     = true
}

provider "aws" {
  region = var.region
}

# ──────────────────────────────────────────────────────────────────────
# DynamoDB Table
# ──────────────────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "audit_events" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  # Primary key: service_date (PK) + ts_event (SK)
  hash_key  = "service_date"
  range_key = "ts_event"

  attribute {
    name = "service_date"
    type = "S"
  }

  attribute {
    name = "ts_event"
    type = "S"
  }

  # GSI key attributes
  attribute {
    name = "patient_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "actor_subject_id"
    type = "S"
  }

  attribute {
    name = "outcome_status"
    type = "S"
  }

  # GSI1: patient_id-index
  # "Show all access to patient X in the last 90 days"
  # HIPAA §164.312(b) audit controls, access review
  global_secondary_index {
    name            = "patient_id-index"
    hash_key        = "patient_id"
    range_key       = "timestamp"
    projection_type = "INCLUDE"

    non_key_attributes = [
      "event_id",
      "action_type",
      "actor_subject_id",
      "outcome_status",
      "data_classification",
      "http_route_template",
    ]
  }

  # GSI2: actor-index
  # "Show all actions by user Y in the last 30 days"
  # HIPAA §164.308(a)(1)(ii)(D) information system activity review
  global_secondary_index {
    name            = "actor-index"
    hash_key        = "actor_subject_id"
    range_key       = "timestamp"
    projection_type = "INCLUDE"

    non_key_attributes = [
      "event_id",
      "action_type",
      "resource_type",
      "patient_id",
      "outcome_status",
      "http_route_template",
    ]
  }

  # GSI3: outcome-index
  # "Show all DENIED or FAILED access attempts"
  # HIPAA §164.308(a)(5)(ii)(C) log-in monitoring, access denial review
  global_secondary_index {
    name            = "outcome-index"
    hash_key        = "outcome_status"
    range_key       = "timestamp"
    projection_type = "INCLUDE"

    non_key_attributes = [
      "event_id",
      "actor_subject_id",
      "action_type",
      "resource_type",
      "patient_id",
      "error_type",
    ]
  }

  # TTL: DynamoDB automatically deletes items whose `ttl` attribute
  # is past the current epoch. Free, no write capacity consumed.
  ttl {
    enabled        = var.ttl_enabled
    attribute_name = "ttl"
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Project     = "bh-healthcare"
    Component   = "audit"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ──────────────────────────────────────────────────────────────────────
# IAM Policy — minimum permissions for the application
# ──────────────────────────────────────────────────────────────────────

resource "aws_iam_policy" "audit_writer" {
  name        = "bh-audit-dynamodb-writer-${var.environment}"
  description = "Minimum DynamoDB permissions for bh-fastapi-audit DynamoDBSink"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AuditEventWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:DescribeTable",
        ]
        Resource = aws_dynamodb_table.audit_events.arn
      },
      {
        Sid    = "AuditEventQuery"
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
        ]
        Resource = [
          aws_dynamodb_table.audit_events.arn,
          "${aws_dynamodb_table.audit_events.arn}/index/*",
        ]
      },
    ]
  })
}

# ──────────────────────────────────────────────────────────────────────
# Outputs
# ──────────────────────────────────────────────────────────────────────

output "table_name" {
  description = "DynamoDB table name (pass to DynamoDBSink)"
  value       = aws_dynamodb_table.audit_events.name
}

output "table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.audit_events.arn
}

output "writer_policy_arn" {
  description = "IAM policy ARN to attach to the application role"
  value       = aws_iam_policy.audit_writer.arn
}

output "region" {
  description = "AWS region (pass to DynamoDBSink or set AWS_DEFAULT_REGION)"
  value       = var.region
}
