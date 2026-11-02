output "sns_topic_arn" {
  description = "ARN of the SNS topic for cost notifications (null when the email channel is disabled)"
  value       = one(aws_sns_topic.cost_notification[*].arn)
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.cost_notifier.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.cost_notifier.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.daily_trigger.name
}

output "eventbridge_schedule" {
  description = "Schedule expression for the EventBridge rule"
  value       = aws_cloudwatch_event_rule.daily_trigger.schedule_expression
}

output "notification_channels" {
  description = "Enabled notification channels"
  value       = var.notification_channels
}

output "notification_email" {
  description = "Email address receiving notifications"
  value       = var.notification_email
  sensitive   = true
}

