variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "notification_channels" {
  description = "Notification channels to use: \"slack\", \"email\", or both (e.g. [\"slack\", \"email\"])"
  type        = list(string)
  default     = ["slack"]

  validation {
    condition = (
      length(var.notification_channels) > 0 &&
      alltrue([for c in var.notification_channels : contains(["slack", "email"], c)])
    )
    error_message = "notification_channels must be a non-empty list containing only \"slack\" and/or \"email\"."
  }
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL (required when notification_channels contains \"slack\")"
  type        = string
  default     = ""
  sensitive   = true

  validation {
    condition     = var.slack_webhook_url == "" || startswith(var.slack_webhook_url, "https://hooks.slack.com/")
    error_message = "slack_webhook_url must start with https://hooks.slack.com/."
  }
}

variable "notification_email" {
  description = "Email address to receive notifications (required when notification_channels contains \"email\")"
  type        = string
  default     = ""
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (default: 9 AM JST daily)"
  type        = string
  default     = "cron(0 0 * * ? *)" # UTC 00:00 = JST 09:00
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "daily-cost-monitor"
}

variable "days_to_check" {
  description = "Number of days to retrieve cost data"
  type        = number
  default     = 7
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "system_name" {
  description = "System name for tagging"
  type        = string
  default     = "dailycost"
}

# Common tags for all resources
locals {
  slack_enabled = contains(var.notification_channels, "slack")
  email_enabled = contains(var.notification_channels, "email")

  common_tags = {
    env    = var.environment
    system = var.system_name
  }
}

