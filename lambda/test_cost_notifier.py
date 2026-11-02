"""
Unit tests for cost_notifier Lambda function.
Tests all functions with mocked AWS services.
"""

import pytest
import json
from unittest.mock import patch, Mock
from decimal import Decimal


@pytest.mark.unit
class TestGetCostData:
    """Tests for get_cost_data function"""

    def test_get_cost_data_success(self, mock_ce_client, mock_cost_response):
        """Test successful cost data retrieval"""
        with patch("cost_notifier.ce_client", mock_ce_client):
            from cost_notifier import get_cost_data

            result = get_cost_data(days=7)

            assert result is not None
            assert "ResultsByTime" in result
            assert len(result["ResultsByTime"]) == 2
            mock_ce_client.get_cost_and_usage.assert_called_once()

    def test_get_cost_data_with_different_days(self, mock_ce_client):
        """Test cost data retrieval with different day parameters"""
        with patch("cost_notifier.ce_client", mock_ce_client):
            from cost_notifier import get_cost_data

            # Test with 1 day
            result = get_cost_data(days=1)
            assert result is not None

            # Test with 30 days
            result = get_cost_data(days=30)
            assert result is not None

    def test_get_cost_data_exception(self, mock_ce_client_exception):
        """Test cost data retrieval when API raises exception"""
        with patch("cost_notifier.ce_client", mock_ce_client_exception):
            from cost_notifier import get_cost_data

            result = get_cost_data(days=7)

            assert result is None
            mock_ce_client_exception.get_cost_and_usage.assert_called_once()

    def test_get_cost_data_empty_response(self, mock_empty_cost_response):
        """Test cost data retrieval with empty response"""
        mock_client = Mock()
        mock_client.get_cost_and_usage.return_value = mock_empty_cost_response

        with patch("cost_notifier.ce_client", mock_client):
            from cost_notifier import get_cost_data

            result = get_cost_data(days=7)

            assert result is not None
            assert result["ResultsByTime"] == []


@pytest.mark.unit
class TestGetResourceCounts:
    """Tests for get_resource_counts function"""

    def test_get_resource_counts_all_services_success(
        self, mock_ec2_client, mock_rds_client, mock_s3_client, mock_lambda_client
    ):
        """Test resource counts when all services return successfully"""
        with patch("cost_notifier.ec2_client", mock_ec2_client), patch(
            "cost_notifier.rds_client", mock_rds_client
        ), patch("cost_notifier.s3_client", mock_s3_client), patch(
            "cost_notifier.lambda_client", mock_lambda_client
        ):

            from cost_notifier import get_resource_counts

            resources = get_resource_counts()

            assert resources["EC2"]["total"] == 3
            assert resources["EC2"]["running"] == 2
            assert resources["RDS"]["total"] == 1
            assert resources["RDS"]["available"] == 1
            assert resources["S3"]["total_buckets"] == 5
            assert resources["Lambda"]["total_functions"] == 2

    def test_get_resource_counts_ec2_exception(
        self,
        mock_ec2_client_exception,
        mock_rds_client,
        mock_s3_client,
        mock_lambda_client,
    ):
        """Test resource counts when EC2 raises exception"""
        with patch("cost_notifier.ec2_client", mock_ec2_client_exception), patch(
            "cost_notifier.rds_client", mock_rds_client
        ), patch("cost_notifier.s3_client", mock_s3_client), patch(
            "cost_notifier.lambda_client", mock_lambda_client
        ):

            from cost_notifier import get_resource_counts

            resources = get_resource_counts()

            # EC2 should have zero counts due to exception
            assert resources["EC2"]["total"] == 0
            assert resources["EC2"]["running"] == 0

            # Other services should still work
            assert resources["RDS"]["total"] == 1
            assert resources["S3"]["total_buckets"] == 5
            assert resources["Lambda"]["total_functions"] == 2

    def test_get_resource_counts_all_exceptions(
        self,
        mock_ec2_client_exception,
        mock_rds_client_exception,
        mock_s3_client_exception,
        mock_lambda_client_exception,
    ):
        """Test resource counts when all services raise exceptions"""
        with patch("cost_notifier.ec2_client", mock_ec2_client_exception), patch(
            "cost_notifier.rds_client", mock_rds_client_exception
        ), patch("cost_notifier.s3_client", mock_s3_client_exception), patch(
            "cost_notifier.lambda_client", mock_lambda_client_exception
        ):

            from cost_notifier import get_resource_counts

            resources = get_resource_counts()

            # All should have zero/empty counts
            assert resources["EC2"]["total"] == 0
            assert resources["EC2"]["running"] == 0
            assert resources["RDS"]["total"] == 0
            assert resources["RDS"]["available"] == 0
            assert resources["S3"]["total_buckets"] == 0
            assert resources["Lambda"]["total_functions"] == 0

    def test_get_resource_counts_empty_resources(self):
        """Test resource counts with no resources"""
        mock_ec2 = Mock()
        mock_ec2.describe_instances.return_value = {"Reservations": []}

        mock_rds = Mock()
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}

        mock_s3 = Mock()
        mock_s3.list_buckets.return_value = {"Buckets": []}

        mock_lambda = Mock()
        mock_lambda.list_functions.return_value = {"Functions": []}

        with patch("cost_notifier.ec2_client", mock_ec2), patch(
            "cost_notifier.rds_client", mock_rds
        ), patch("cost_notifier.s3_client", mock_s3), patch(
            "cost_notifier.lambda_client", mock_lambda
        ):

            from cost_notifier import get_resource_counts

            resources = get_resource_counts()

            assert resources["EC2"]["total"] == 0
            assert resources["EC2"]["running"] == 0
            assert resources["RDS"]["total"] == 0
            assert resources["S3"]["total_buckets"] == 0
            assert resources["Lambda"]["total_functions"] == 0


@pytest.mark.unit
class TestFormatCostMessage:
    """Tests for format_cost_message function"""

    def test_format_cost_message_with_valid_data(
        self, mock_cost_response, mock_resource_data
    ):
        """Test message formatting with valid cost and resource data"""
        from cost_notifier import format_cost_message

        message = format_cost_message(mock_cost_response, mock_resource_data, 7)

        # Check for Japanese text
        assert "AWS 日次レポート" in message
        assert "コスト情報" in message
        assert "リソース情報" in message

        # Check for cost information
        assert "2024-01-01" in message
        assert "2024-01-02" in message
        assert "$" in message

        # Check for resource information
        assert "EC2 インスタンス" in message
        assert "RDS インスタンス" in message
        assert "S3 バケット" in message
        assert "Lambda 関数" in message

        # Check for resource counts
        assert "総数: 3" in message  # EC2 total
        assert "稼働中: 2" in message  # EC2 running
        assert "総数: 1" in message  # RDS total
        assert "総数: 5" in message  # S3 buckets
        assert "総数: 2" in message  # Lambda functions

    def test_format_cost_message_with_none_cost_data(self, mock_resource_data):
        """Test message formatting when cost data is None"""
        from cost_notifier import format_cost_message

        message = format_cost_message(None, mock_resource_data, 7)

        assert "コストデータの取得に失敗しました" in message

    def test_format_cost_message_unicode_preservation(
        self, mock_cost_response, mock_resource_data
    ):
        """Test that Japanese characters are properly preserved"""
        from cost_notifier import format_cost_message

        message = format_cost_message(mock_cost_response, mock_resource_data, 7)

        # Verify specific Japanese characters and emojis
        assert "📅" in message
        assert "💰" in message
        assert "🔧" in message
        assert "📦" in message
        assert "🗄️" in message
        assert "🪣" in message
        assert "λ" in message

    def test_format_cost_message_decimal_precision(
        self, mock_cost_response, mock_resource_data
    ):
        """Test that decimal currency values are formatted correctly"""
        from cost_notifier import format_cost_message

        message = format_cost_message(mock_cost_response, mock_resource_data, 7)

        # Check for properly formatted currency (2 decimal places)
        assert ".50" in message or ".25" in message or ".00" in message

    def test_format_cost_message_different_days(
        self, mock_cost_response, mock_resource_data
    ):
        """Test message formatting with different day parameters"""
        from cost_notifier import format_cost_message

        # Test with 1 day
        message_1 = format_cost_message(mock_cost_response, mock_resource_data, 1)
        assert "過去1日間" in message_1

        # Test with 30 days
        message_30 = format_cost_message(mock_cost_response, mock_resource_data, 30)
        assert "過去30日間" in message_30


@pytest.mark.unit
class TestSendNotification:
    """Tests for send_notification function"""

    def test_send_notification_success(self, mock_sns_client):
        """Test successful SNS notification"""
        with patch("cost_notifier.sns_client", mock_sns_client):
            from cost_notifier import send_notification

            message = "Test message"
            topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"

            result = send_notification(message, topic_arn)

            assert result is True
            mock_sns_client.publish.assert_called_once()
            call_args = mock_sns_client.publish.call_args
            assert call_args[1]["TopicArn"] == topic_arn
            assert call_args[1]["Message"] == message
            assert "Subject" in call_args[1]

    def test_send_notification_exception(self, mock_sns_client_exception):
        """Test SNS notification when exception occurs"""
        with patch("cost_notifier.sns_client", mock_sns_client_exception):
            from cost_notifier import send_notification

            message = "Test message"
            topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"

            result = send_notification(message, topic_arn)

            assert result is False
            mock_sns_client_exception.publish.assert_called_once()


@pytest.mark.unit
class TestFormatSlackPayload:
    """Tests for format_slack_payload function"""

    def _texts(self, payload):
        """Collect every text string in the blocks"""
        texts = []
        for block in payload["blocks"]:
            if "text" in block:
                texts.append(block["text"]["text"])
            for field in block.get("fields", []):
                texts.append(field["text"])
            for element in block.get("elements", []):
                texts.append(element["text"])
        return "\n".join(texts)

    def test_payload_structure(self, mock_cost_response, mock_resource_data):
        from cost_notifier import format_slack_payload

        payload = format_slack_payload(mock_cost_response, mock_resource_data, 7)

        assert "AWS 日次レポート" in payload["text"]
        assert payload["blocks"][0]["type"] == "header"
        # Slack limits: 50 blocks, 3000 chars per section text, 10 fields
        assert len(payload["blocks"]) <= 50
        for block in payload["blocks"]:
            if "text" in block and block["type"] == "section":
                assert len(block["text"]["text"]) <= 3000
            assert len(block.get("fields", [])) <= 10
        # Must be JSON serializable
        json.dumps(payload)

    def test_payload_contains_costs_and_resources(
        self, mock_cost_response, mock_resource_data
    ):
        from cost_notifier import format_slack_payload

        text = self._texts(
            format_slack_payload(mock_cost_response, mock_resource_data, 7)
        )

        assert "日別コスト" in text
        assert "サービス別コスト" in text
        assert "$" in text
        assert f"総数 {mock_resource_data['EC2']['total']}" in text

    def test_payload_with_none_cost_data(self, mock_resource_data):
        from cost_notifier import format_slack_payload

        payload = format_slack_payload(None, mock_resource_data, 7)

        assert "コストデータの取得に失敗しました" in payload["text"]
        assert "blocks" not in payload

    def test_payload_with_empty_results(self, mock_resource_data):
        from cost_notifier import format_slack_payload

        payload = format_slack_payload({"ResultsByTime": []}, mock_resource_data, 7)

        assert "データなし" in self._texts(payload)

    def test_service_names_are_escaped(self, mock_resource_data):
        from cost_notifier import format_slack_payload

        cost_data = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-11-01", "End": "2026-11-02"},
                    "Groups": [
                        {
                            "Keys": ["A&B <svc>"],
                            "Metrics": {"UnblendedCost": {"Amount": "5.00"}},
                        }
                    ],
                }
            ]
        }
        text = self._texts(format_slack_payload(cost_data, mock_resource_data, 1))

        assert "A&amp;B &lt;svc&gt;" in text


@pytest.mark.unit
class TestSendSlackNotification:
    """Tests for send_slack_notification function"""

    WEBHOOK = "https://hooks.slack.com/services/T000/B000/XXXX"

    def _mock_response(self, status=200, body=b"ok"):
        response = Mock()
        response.status = status
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def test_send_slack_notification_success(self):
        with patch(
            "cost_notifier.urllib.request.urlopen", return_value=self._mock_response()
        ) as mock_urlopen:
            from cost_notifier import send_slack_notification

            result = send_slack_notification(
                {"text": "Test message 日本語"}, self.WEBHOOK
            )

            assert result is True
            request = mock_urlopen.call_args[0][0]
            assert request.full_url == self.WEBHOOK
            assert request.get_method() == "POST"
            payload = json.loads(request.data.decode("utf-8"))
            assert payload == {"text": "Test message 日本語"}

    def test_send_slack_notification_non_200(self):
        with patch(
            "cost_notifier.urllib.request.urlopen",
            return_value=self._mock_response(status=500, body=b"error"),
        ):
            from cost_notifier import send_slack_notification

            assert send_slack_notification({"text": "Test"}, self.WEBHOOK) is False

    def test_send_slack_notification_exception(self, capsys):
        with patch(
            "cost_notifier.urllib.request.urlopen", side_effect=Exception("boom")
        ):
            from cost_notifier import send_slack_notification

            assert send_slack_notification({"text": "Test"}, self.WEBHOOK) is False
            # The webhook URL is a secret and must not be logged
            assert self.WEBHOOK not in capsys.readouterr().out


@pytest.mark.integration
class TestLambdaHandler:
    """Integration tests for lambda_handler function"""

    def test_lambda_handler_success(
        self,
        mock_environment,
        mock_ce_client,
        mock_sns_client,
        mock_ec2_client,
        mock_rds_client,
        mock_s3_client,
        mock_lambda_client,
    ):
        """Test successful lambda handler execution"""
        with patch("cost_notifier.ce_client", mock_ce_client), patch(
            "cost_notifier.sns_client", mock_sns_client
        ), patch("cost_notifier.ec2_client", mock_ec2_client), patch(
            "cost_notifier.rds_client", mock_rds_client
        ), patch(
            "cost_notifier.s3_client", mock_s3_client
        ), patch(
            "cost_notifier.lambda_client", mock_lambda_client
        ):

            from cost_notifier import lambda_handler

            response = lambda_handler({}, None)

            assert response["statusCode"] == 200
            assert "Report sent successfully" in response["body"]
            mock_ce_client.get_cost_and_usage.assert_called_once()
            mock_sns_client.publish.assert_called_once()

    def test_lambda_handler_missing_sns_topic_arn(self, monkeypatch):
        """Test lambda handler when SNS_TOPIC_ARN is not set"""
        # Remove SNS_TOPIC_ARN from environment
        monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)

        from cost_notifier import lambda_handler

        response = lambda_handler({}, None)

        assert response["statusCode"] == 500
        assert "SNS_TOPIC_ARN not configured" in response["body"]

    def test_lambda_handler_with_custom_days(
        self,
        monkeypatch,
        mock_ce_client,
        mock_sns_client,
        mock_ec2_client,
        mock_rds_client,
        mock_s3_client,
        mock_lambda_client,
    ):
        """Test lambda handler with custom DAYS_TO_CHECK"""
        monkeypatch.setenv(
            "SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:test-topic"
        )
        monkeypatch.setenv("DAYS_TO_CHECK", "30")

        with patch("cost_notifier.ce_client", mock_ce_client), patch(
            "cost_notifier.sns_client", mock_sns_client
        ), patch("cost_notifier.ec2_client", mock_ec2_client), patch(
            "cost_notifier.rds_client", mock_rds_client
        ), patch(
            "cost_notifier.s3_client", mock_s3_client
        ), patch(
            "cost_notifier.lambda_client", mock_lambda_client
        ):

            from cost_notifier import lambda_handler

            response = lambda_handler({}, None)

            assert response["statusCode"] == 200

    def test_lambda_handler_sns_failure(
        self,
        mock_environment,
        mock_ce_client,
        mock_sns_client_exception,
        mock_ec2_client,
        mock_rds_client,
        mock_s3_client,
        mock_lambda_client,
    ):
        """Test lambda handler when SNS notification fails"""
        with patch("cost_notifier.ce_client", mock_ce_client), patch(
            "cost_notifier.sns_client", mock_sns_client_exception
        ), patch("cost_notifier.ec2_client", mock_ec2_client), patch(
            "cost_notifier.rds_client", mock_rds_client
        ), patch(
            "cost_notifier.s3_client", mock_s3_client
        ), patch(
            "cost_notifier.lambda_client", mock_lambda_client
        ):

            from cost_notifier import lambda_handler

            response = lambda_handler({}, None)

            assert response["statusCode"] == 500
            assert "Failed to send report" in response["body"]


@pytest.mark.integration
class TestLambdaHandlerChannels:
    """Tests for notification channel selection in lambda_handler"""

    def _run(self, monkeypatch, env, mock_ce_client, mock_cost_response):
        for key in ("NOTIFICATION_CHANNELS", "SNS_TOPIC_ARN", "SLACK_WEBHOOK_URL"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        mock_ce_client.get_cost_and_usage.return_value = mock_cost_response
        with patch("cost_notifier.ce_client", mock_ce_client), patch(
            "cost_notifier.get_resource_counts", return_value={}
        ), patch("cost_notifier.format_cost_message", return_value="msg"), patch(
            "cost_notifier.format_slack_payload", return_value={"text": "msg"}
        ), patch(
            "cost_notifier.send_notification", return_value=True
        ) as email, patch(
            "cost_notifier.send_slack_notification", return_value=True
        ) as slack:
            from cost_notifier import lambda_handler

            return lambda_handler({}, None), email, slack

    def test_slack_only(self, monkeypatch, mock_ce_client, mock_cost_response):
        response, email, slack = self._run(
            monkeypatch,
            {"NOTIFICATION_CHANNELS": "slack", "SLACK_WEBHOOK_URL": "https://x"},
            mock_ce_client,
            mock_cost_response,
        )
        assert response["statusCode"] == 200
        slack.assert_called_once()
        email.assert_not_called()

    def test_both_channels(self, monkeypatch, mock_ce_client, mock_cost_response):
        response, email, slack = self._run(
            monkeypatch,
            {
                "NOTIFICATION_CHANNELS": "slack,email",
                "SLACK_WEBHOOK_URL": "https://x",
                "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:t",
            },
            mock_ce_client,
            mock_cost_response,
        )
        assert response["statusCode"] == 200
        slack.assert_called_once()
        email.assert_called_once()

    def test_missing_webhook_url(self, monkeypatch, mock_ce_client, mock_cost_response):
        response, email, slack = self._run(
            monkeypatch,
            {"NOTIFICATION_CHANNELS": "slack"},
            mock_ce_client,
            mock_cost_response,
        )
        assert response["statusCode"] == 500
        assert "SLACK_WEBHOOK_URL not configured" in response["body"]
        slack.assert_not_called()

    def test_invalid_channel(self, monkeypatch, mock_ce_client, mock_cost_response):
        response, _, _ = self._run(
            monkeypatch,
            {"NOTIFICATION_CHANNELS": "teams"},
            mock_ce_client,
            mock_cost_response,
        )
        assert response["statusCode"] == 500
        assert "NOTIFICATION_CHANNELS is invalid" in response["body"]
