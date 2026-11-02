# Slack 通知セットアップガイド

日次レポートを Slack に通知するための、Slack App の作成と Incoming Webhook の発行手順です。
所要時間は約 5 分です。

## 📋 事前に必要なもの

- 通知先の Slack ワークスペースで App を追加できる権限
  - 権限がない場合は、ワークスペース管理者に承認を依頼してください（[承認依頼が必要な場合](#承認依頼が必要な場合)を参照）
- 通知を受け取る Slack チャンネル（例: `#aws-cost`）

## 🔧 手順 1: Slack App を作成する

1. ブラウザで <https://api.slack.com/apps> を開き、Slack にログインします
2. 右上の **Create New App** をクリックします
3. **From scratch** を選択します
4. 次の項目を入力します
   - **App Name**: 任意（例: `AWS Daily Cost Monitor`）
   - **Pick a workspace to develop your app in**: 通知先のワークスペースを選択
5. **Create App** をクリックします

## 🔗 手順 2: Incoming Webhook を有効化して URL を発行する

1. 左メニューの **Features** → **Incoming Webhooks** を開きます
2. **Activate Incoming Webhooks** のスイッチを **On** にします
3. ページ下部の **Add New Webhook to Workspace** をクリックします
4. 通知先のチャンネルを選択し、**許可する（Allow）** をクリックします
5. **Webhook URLs for Your Workspace** の一覧に、次の形式の URL が追加されます

   ```text
   https://hooks.slack.com/services/<TEAM_ID>/<BOT_ID>/<SECRET>
   ```

6. **Copy** をクリックして URL をコピーします

> ⚠️ **この URL はパスワードと同じ扱いです。**
> URL を知っている人は誰でも、そのチャンネルに投稿できます。
> Git へのコミット、チャットへの貼り付け、スクリーンショットの共有はしないでください。

## 🧪 手順 3: Webhook の動作確認（任意）

デプロイ前に、URL が正しく動くか確認できます。

```bash
# URL は手元のシェルにだけ設定する（履歴に残したくない場合は先頭にスペースを入れる）
export SLACK_WEBHOOK_URL="コピーした URL"

curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Webhook のテスト投稿です"}' \
  "$SLACK_WEBHOOK_URL"
```

`ok` と表示され、チャンネルにメッセージが届けば成功です。

## 🚀 手順 4: Terraform に設定する

Webhook URL は秘密情報です。次のどちらかの方法で渡してください。

### 方法 A: 環境変数で渡す（推奨）

ファイルに URL が残らないため、こちらを推奨します。

```bash
export TF_VAR_slack_webhook_url="コピーした URL"
```

`terraform/terraform.tfvars` には、チャンネルの設定だけ書きます。

```hcl
notification_channels = ["slack"]
```

### 方法 B: terraform.tfvars に書く

```hcl
notification_channels = ["slack"]
slack_webhook_url     = "コピーした URL"
```

`terraform.tfvars` は `.gitignore` に含まれています。コミットしないよう注意してください。

### デプロイ

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

> 💡 Terraform の state ファイルには Webhook URL が平文で保存されます（Lambda の環境変数として管理されるため）。
> state をリモートバックエンドで共有する場合は、アクセス権限を適切に絞ってください。

## ✅ 手順 5: 動作テスト

```bash
aws lambda invoke \
  --function-name daily-cost-monitor-function \
  --region ap-northeast-1 \
  output.json

cat output.json
```

`{"statusCode": 200, ...}` が返り、Slack にレポートが投稿されれば完了です。

## 🔀 通知先の切り替え

`terraform.tfvars` の `notification_channels` を変更して `terraform apply` するだけで切り替えられます。

- `["slack"]`（デフォルト）: Slack のみ。SNS トピックなどのメール関連リソースは作成されません
- `["email"]`: メールのみ。`notification_email` の設定が必要です
- `["slack", "email"]`: 両方に送信。両方の設定が必要です

```hcl
# Slack からメールに戻す例
notification_channels = ["email"]
notification_email    = "your-email@example.com"
```

メールに切り替えた場合は、SNS から届く **Subscription Confirmation** メールの承認が必要です。

## 🛠 トラブルシューティング

### Slack に投稿されない

1. Lambda のログを確認します

   ```bash
   aws logs tail /aws/lambda/daily-cost-monitor-function --since 1h --region ap-northeast-1
   ```

2. ログに出ているメッセージを確認します

   - `SLACK_WEBHOOK_URL not configured`: `slack_webhook_url` が未設定です。設定して `terraform apply` し直してください
   - `HTTP Error 404`（`no_service`）: URL が間違っているか、Webhook が削除されています。URL を発行し直してください
   - `HTTP Error 403`（`invalid_token`）: Webhook が無効化されています。URL を発行し直してください
   - `HTTP Error 404`（`channel_not_found`）: 投稿先チャンネルが削除またはアーカイブされています。Webhook を作り直してください
   - `timed out`: Lambda から Slack への通信に失敗しています。VPC 内に配置している場合は NAT を確認してください

### 投稿先のチャンネルを変えたい

Webhook URL は 1 つのチャンネルに紐づいています。

1. [Slack App の管理画面](https://api.slack.com/apps) → 対象の App → **Incoming Webhooks**
2. **Add New Webhook to Workspace** で、新しいチャンネル用の URL を発行
3. `slack_webhook_url` を新しい URL に更新して `terraform apply`

### Webhook URL が漏れた可能性がある

1. **Incoming Webhooks** のページで、該当の URL の **Remove** をクリックして無効化
2. 新しい URL を発行
3. `slack_webhook_url` を更新して `terraform apply`

## 承認依頼が必要な場合

ワークスペースの設定によっては、App の追加に管理者の承認が必要です。
手順 1 の後や手順 2 で承認待ちの表示が出た場合は、管理者に次の内容を伝えてください。

- 目的: AWS の日次コストレポートを `#（チャンネル名）` に投稿するための Incoming Webhook
- 必要な権限: Incoming Webhooks のみ（チャンネルへの投稿のみ。メッセージの読み取りはできません）

## 📚 参考リンク

- [Sending messages using incoming webhooks（Slack 公式）](https://api.slack.com/messaging/webhooks)
