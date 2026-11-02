# AWS Daily Cost and Resource Monitor

[![CI/CD](https://github.com/Canale0107/aws-daily-cost-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/Canale0107/aws-daily-cost-monitor/actions/workflows/ci.yml)

この Terraform プロジェクトは、AWS 上の毎日のコスト状況とリソース取得状況を自動的に取得し、Slack（またはメール）で通知する仕組みを構築します。

## 機能

- **毎日のコストレポート**: 過去 N 日間の AWS コストをサービス別に集計
- **リソース情報**: EC2、RDS、S3、Lambda 等の主要リソースの数を取得
- **Slack / メール通知**: Slack の Incoming Webhook、またはメールに自動送信（`notification_channels` で切り替え可能）
- **スケジュール実行**: EventBridge（CloudWatch Events）による定期実行

## アーキテクチャ

```
EventBridge (日次トリガー)
    ↓
Lambda関数
    ├─→ AWS Cost Explorer (コスト情報取得)
    ├─→ EC2/RDS/S3/Lambda (リソース情報取得)
    ├─→ Slack Incoming Webhook (Slack 通知)
    └─→ SNS (メール通知。メールを有効にした場合のみ)
```

![構成図](/diagrams/overview.drawio.svg)

## 構成要素

- **EventBridge Rule**: 毎日指定時刻に Lambda 関数をトリガー
- **Lambda Function**: コストとリソース情報を取得・整形
- **SNS Topic**: メール通知を配信（`notification_channels` に `email` を含めた場合のみ作成）
- **IAM Roles**: 必要な権限を付与

すべてのリソースには以下のタグが自動的に付与されます：

- `Name`: `{environment}-{system_name}-{リソース名}`
- `env`: `{environment}`（デフォルト: dev）
- `system`: `{system_name}`（デフォルト: dailycost）

## 前提条件

- Terraform >= 1.3
- AWS CLI 設定済み（認証情報が設定されていること）
- Slack Incoming Webhook の URL（発行手順は [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md) を参照）
  - メール通知を使う場合は、代わりにメールアドレスを用意
- 適切な IAM 権限（詳細は [TERRAFORM_SETUP.md](TERRAFORM_SETUP.md) を参照）

## セットアップ手順

### 0. IAM 権限の設定（初回のみ）

Terraform を実行するための IAM 権限が必要です。詳細は [TERRAFORM_SETUP.md](TERRAFORM_SETUP.md) を参照してください。

**簡単セットアップ（IAM ユーザー作成）:**

```bash
./setup-iam.sh
```

このスクリプトは以下を自動で実行します：

- 必要な権限を持つ IAM ポリシーの作成
- Terraform 実行用 IAM ユーザーの作成
- アクセスキーの生成と AWS CLI プロファイルへの追加

### 1. リポジトリのクローンとディレクトリ移動

```bash
cd daily-cost
```

### 2. 設定ファイルの作成

```bash
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集して、必要な値を設定：

```hcl
aws_region    = "ap-northeast-1"
project_name  = "daily-cost-monitor"
days_to_check = 7

# 通知先: ["slack"], ["email"], ["slack", "email"] から選択
notification_channels = ["slack"]

# Slack を使う場合（秘密情報。環境変数 TF_VAR_slack_webhook_url での指定を推奨）
slack_webhook_url = "https://hooks.slack.com/services/XXXX/XXXX/XXXX"

# メールを使う場合
# notification_email = "your-email@example.com"

# Environment and system tags
environment = "dev"
system_name = "dailycost"

# スケジュール設定（デフォルト: 毎日 UTC 00:00 = JST 09:00）
schedule_expression = "cron(0 0 * * ? *)"
```

### 3. AWS 認証情報の設定

```bash
# setup-iam.sh で作成したプロファイルを使用
export AWS_PROFILE=daily-cost-terraform

# または、既存の認証情報を使用
export AWS_PROFILE=your-profile
```

### 4. Terraform ディレクトリに移動

```bash
cd terraform
```

### 5. Terraform の初期化

```bash
terraform init
```

### 6. プランの確認

```bash
terraform plan
```

### 7. リソースの作成

```bash
terraform apply
```

メール通知を有効にした場合は、指定したメールアドレスに **SNS サブスクリプションの確認メール** が届きます。
メール内の確認リンクをクリックして、サブスクリプションを有効化してください。

Slack のみの場合、確認作業は不要です。

### 8. 動作確認（オプション）

Lambda 関数を手動で実行してテストできます：

```bash
aws lambda invoke \
  --function-name daily-cost-monitor-function \
  --region ap-northeast-1 \
  output.json

cat output.json
```

## スケジュール設定

`schedule_expression` 変数で EventBridge のスケジュールを設定できます（UTC 時刻）。

### 例

```hcl
# 毎日 UTC 00:00（JST 09:00）
schedule_expression = "cron(0 0 * * ? *)"

# 毎日 UTC 12:00（JST 21:00）
schedule_expression = "cron(0 12 * * ? *)"

# 平日のみ UTC 01:00（JST 10:00）
schedule_expression = "cron(0 1 ? * MON-FRI *)"
```

## レポート内容

Slack またはメールで送信されるレポートには以下の情報が含まれます：

### コスト情報

- 日別のコスト推移
- 期間中の合計コストと 1 日平均
- サービス別コスト（上位 10 件）

### リソース情報

- **EC2**: インスタンス総数と稼働中の数
- **RDS**: インスタンス総数と利用可能な数
- **S3**: バケット数
- **Lambda**: 関数数

## カスタマイズ

### 追加のリソース情報を取得する

`lambda/cost_notifier.py` の `get_resource_counts()` 関数を編集して、他の AWS サービスの情報を追加できます。

```python
# 例: ECS タスク数を追加
ecs_client = boto3.client('ecs')
clusters = ecs_client.list_clusters()
# ... 処理を追加
```

### レポートフォーマットの変更

`lambda/cost_notifier.py` の `format_cost_message()` 関数を編集して、レポートの表示形式を変更できます。

## コスト

このソリューションの実行にかかる主なコストは以下の通りです：

- **Lambda**: 月に 1 回程度の実行で数セント以下
- **EventBridge**: 無料枠内
- **SNS**（メール通知のみ）: メール配信は月 1000 件まで無料
- **Slack Incoming Webhook**: 無料
- **Cost Explorer API**: 1 リクエストあたり $0.01（月 30 回で約$0.30）

月額コスト: **約$0.50 以下**

## トラブルシューティング

### Slack に投稿されない

[docs/SLACK_SETUP.md のトラブルシューティング](docs/SLACK_SETUP.md#トラブルシューティング) を参照してください。

### メールが届かない

1. SNS サブスクリプションが確認済みか確認

   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn $(terraform output -raw sns_topic_arn)
   ```

2. 迷惑メールフォルダを確認

### Lambda 関数のエラー

CloudWatch Logs でエラーログを確認：

```bash
aws logs tail /aws/lambda/daily-cost-monitor-function \
  --follow \
  --region ap-northeast-1
```

### IAM 権限エラー

Lambda 関数の IAM ロールに必要な権限があるか確認してください。
Cost Explorer API へのアクセスには `ce:GetCostAndUsage` 権限が必要です。

## クリーンアップ

### Terraform リソースの削除

```bash
cd terraform
terraform destroy
```

### IAM リソースの削除（オプション）

setup-iam.sh で作成した IAM ユーザーとポリシーを削除する場合：

```bash
./cleanup-iam.sh
```

## CI/CD

[![CI/CD](https://github.com/Canale0107/aws-daily-cost-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/Canale0107/aws-daily-cost-monitor/actions/workflows/ci.yml)

このプロジェクトには GitHub Actions による自動テストが組み込まれています。

### 実行されるテスト

**Terraform**

- フォーマットチェック (`terraform fmt`)
- 構文検証 (`terraform validate`)
- セキュリティスキャン (`tfsec`)

**Python**

- コードフォーマットチェック (`black`)
- コード品質チェック (`pylint`)
- セキュリティスキャン (`bandit`)
- ユニットテスト + カバレッジ (`pytest`)

### ローカルでのテスト実行

#### 1. 開発用依存関係のインストール

```bash
cd lambda
pip install -r requirements-dev.txt
```

#### 2. テストの実行

```bash
# すべてのテストを実行
pytest

# カバレッジ付きで実行
pytest --cov=. --cov-report=html

# カバレッジレポートを確認
open htmlcov/index.html
```

#### 3. コード品質チェック

```bash
# フォーマットチェック
black --check lambda/

# フォーマット自動修正
black lambda/

# Pylint
pylint lambda/cost_notifier.py

# Bandit セキュリティスキャン
bandit -r lambda/
```

#### 4. Terraform チェック

```bash
cd terraform

# フォーマットチェック
terraform fmt -check

# フォーマット自動修正
terraform fmt

# 検証
terraform validate

# セキュリティスキャン
tfsec .
```

## ライセンス

MIT License

## 参考リンク

- [AWS Cost Explorer API](https://docs.aws.amazon.com/cost-management/latest/APIReference/Welcome.html)
- [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon SNS](https://docs.aws.amazon.com/sns/)
