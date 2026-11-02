# SNS topic for email notifications (created only when the "email" channel is enabled)
resource "aws_sns_topic" "cost_notification" {
  count        = local.email_enabled ? 1 : 0
  name         = "${var.project_name}-topic"
  display_name = "Daily AWS Cost and Resource Notification"

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-${var.system_name}-topic"
    }
  )
}

# SNS topic subscription
resource "aws_sns_topic_subscription" "cost_notification_email" {
  count     = local.email_enabled ? 1 : 0
  topic_arn = aws_sns_topic.cost_notification[0].arn
  protocol  = "email"
  endpoint  = var.notification_email

  lifecycle {
    precondition {
      condition     = var.notification_email != ""
      error_message = "notification_email is required when notification_channels contains \"email\"."
    }
  }
}

# SNS topic policy to allow Lambda to publish
resource "aws_sns_topic_policy" "cost_notification_policy" {
  count = local.email_enabled ? 1 : 0
  arn   = aws_sns_topic.cost_notification[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.cost_notification[0].arn
      }
    ]
  })
}

