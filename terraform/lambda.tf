# Archive Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/lambda_function.zip"
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-${var.system_name}-lambda-role"
    }
  )
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "rds:Describe*",
          "s3:ListAllMyBuckets",
          "lambda:ListFunctions",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      ],
      local.email_enabled ? [
        {
          Effect   = "Allow"
          Action   = ["sns:Publish"]
          Resource = aws_sns_topic.cost_notification[0].arn
        }
      ] : []
    )
  })
}

# Lambda function
resource "aws_lambda_function" "cost_notifier" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-function"
  role             = aws_iam_role.lambda_role.arn
  handler          = "cost_notifier.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 256

  environment {
    variables = merge(
      {
        NOTIFICATION_CHANNELS = join(",", var.notification_channels)
        DAYS_TO_CHECK         = var.days_to_check
      },
      local.email_enabled ? { SNS_TOPIC_ARN = aws_sns_topic.cost_notification[0].arn } : {},
      local.slack_enabled ? { SLACK_WEBHOOK_URL = var.slack_webhook_url } : {}
    )
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy
  ]

  lifecycle {
    precondition {
      condition     = !local.slack_enabled || var.slack_webhook_url != ""
      error_message = "slack_webhook_url is required when notification_channels contains \"slack\"."
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-${var.system_name}-function"
    }
  )
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.cost_notifier.function_name}"
  retention_in_days = 14

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-${var.system_name}-lambda-logs"
    }
  )
}

