# クイックスタートガイド

このガイドでは、最短で AWS Daily Cost Monitor をセットアップする手順を説明します。

## 📋 前提条件チェックリスト

- [ ] AWS CLI がインストール済み
- [ ] AWS 認証情報が設定済み（管理者権限推奨）
- [ ] Terraform がインストール済み（>= 1.0）
- [ ] Slack Incoming Webhook の URL を用意（[SLACK_SETUP.md](SLACK_SETUP.md) を参照。メール通知なら、メールアドレスを用意）

## 🚀 5 分でセットアップ

### ステップ 1: IAM ユーザーとポリシーを作成

```bash
./setup-iam.sh
```

プロンプトに従って進めてください：

- アクセスキーの作成: `y`
- プロファイルへの追加: `y`
- ファイルへの保存: `y` (オプション)

### ステップ 2: 設定ファイルを準備

```bash
# サンプルファイルをコピー
cp terraform.tfvars.example terraform.tfvars

# エディタで編集（Slack Webhook URL を設定）
vim terraform.tfvars  # または nano, code など
```

**最低限編集が必要な項目:**

```hcl
notification_channels = ["slack"]  # メールなら ["email"]、両方なら ["slack", "email"]
slack_webhook_url     = "https://hooks.slack.com/services/XXXX/XXXX/XXXX"  # ← ここを変更
```

Webhook URL は秘密情報です。ファイルに書かず、`export TF_VAR_slack_webhook_url="..."` で渡すこともできます。
Webhook の発行方法は [SLACK_SETUP.md](SLACK_SETUP.md) を参照してください。メール通知を使う場合は `notification_email` を設定します。

### ステップ 3: Terraform を実行

```bash
# プロファイルを設定
export AWS_PROFILE=daily-cost-terraform

# Terraform ディレクトリに移動
cd terraform

# 初期化
terraform init

# プランを確認（オプション）
terraform plan

# デプロイ
terraform apply
```

`yes` と入力して Enter を押すとデプロイが開始されます。

### ステップ 4: メールを確認（メール通知を有効にした場合のみ）

1. 指定したメールアドレスに **AWS Notification - Subscription Confirmation** という件名のメールが届きます
2. メール内の **Confirm subscription** リンクをクリック
3. ブラウザで確認ページが開いたら完了！

### ステップ 5: テスト（オプション）

```bash
# Lambda関数を手動実行してテスト
aws lambda invoke \
  --function-name daily-cost-monitor-function \
  --region ap-northeast-1 \
  output.json

# 結果を確認
cat output.json
```

数分後、Slack（またはメール）にレポートが届きます。

## ✅ 完了

これで毎日指定した時刻（デフォルト: JST 9:00）にコストレポートが届くようになりました。

## 🎯 次のステップ

### レポートをカスタマイズ

`terraform.tfvars` を編集して設定を変更：

```hcl
# 過去30日分のデータを取得
days_to_check = 30

# 毎日21時（JST）に実行
schedule_expression = "cron(0 12 * * ? *)"

# タグをカスタマイズ
environment = "prod"
system_name = "cost-monitoring"
```

変更後、再度適用：

```bash
terraform apply
```

### Lambda 関数をカスタマイズ

より詳細な情報を取得したい場合は `lambda/cost_notifier.py` を編集してください。

例：

- ECS タスク数の追加
- ElastiCache 情報の追加
- より詳細なコスト分析

## 🧹 削除方法

### 一時的に停止

EventBridge ルールを無効化：

```bash
aws events disable-rule --name daily-cost-monitor-daily-trigger
```

再度有効化：

```bash
aws events enable-rule --name daily-cost-monitor-daily-trigger
```

### 完全に削除

```bash
# Terraformリソースを削除
cd terraform
terraform destroy

# IAMリソースも削除する場合
./cleanup-iam.sh
```

## ❓ トラブルシューティング

### メールが届かない

1. **サブスクリプションを確認**

   ```bash
   aws sns list-subscriptions
   ```

   Status が `Confirmed` になっているか確認

2. **迷惑メールフォルダを確認**

3. **Lambda 関数のログを確認**

   ```bash
   aws logs tail /aws/lambda/daily-cost-monitor-function --follow
   ```

### 権限エラーが出る

```bash
# 現在の認証情報を確認
aws sts get-caller-identity

# 正しいプロファイルを使用しているか確認
echo $AWS_PROFILE
```

詳細は [TERRAFORM_SETUP.md](TERRAFORM_SETUP.md) を参照してください。

### Terraform エラー

```bash
cd terraform

# 状態をクリーンアップ
terraform init -reconfigure

# 再度実行
terraform plan
```

## 📚 詳細ドキュメント

- [README.md](README.md) - 完全なドキュメント
- [TERRAFORM_SETUP.md](TERRAFORM_SETUP.md) - IAM 権限の詳細
- [Lambda 関数のコード](lambda/cost_notifier.py) - カスタマイズ方法

## 💰 コスト見積もり

このソリューションの月額コスト：

| サービス          | 使用量           | コスト            |
| ----------------- | ---------------- | ----------------- |
| Lambda            | 30 回/月 × 5 秒  | ~$0.00 (無料枠内) |
| Cost Explorer API | 30 リクエスト/月 | ~$0.30            |
| EventBridge       | 30 回/月         | $0.00 (無料)      |
| SNS               | 30 メール/月     | $0.00 (無料枠内)  |
| **合計**          |                  | **~$0.30/月**     |

## 🎉 便利な使い方

### Slack に通知を送る

Lambda 関数を修正して Slack Webhook に送信することも可能です。

### 複数環境で使用

環境ごとにディレクトリを分けて管理：

```bash
daily-cost/
├── dev/
│   └── terraform.tfvars
├── staging/
│   └── terraform.tfvars
└── prod/
    └── terraform.tfvars
```

### 週次レポート

平日だけ実行する場合：

```hcl
schedule_expression = "cron(0 0 ? * MON-FRI *)"
```

週次レポート（月曜日のみ）：

```hcl
schedule_expression = "cron(0 0 ? * MON *)"
```

---

**ご不明な点がありましたら、[Issues](https://github.com/your-repo/issues) までお気軽にお問い合わせください！**
