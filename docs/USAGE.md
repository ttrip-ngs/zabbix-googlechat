# 利用ガイド: zabbix-googlechat

## 1. インストール

### 1.1 前提条件

- Python 3.9以上
- pip（Pythonパッケージマネージャー）

### 1.2 インストール

**本番運用（推奨）**

```bash
pip install zabbix-googlechat
```

インストール後、`zabbix-googlechat-notify` コマンドが利用可能になる。

**ローカルリポジトリから**

```bash
pip install /path/to/zabbix-googlechat
```

**開発環境**

```bash
pip install -e ".[dev]"
pre-commit install
```

---

## 2. Google Chat Webhook URLの取得

### 2.1 手順

1. Google ChatでWebhookを設定したいスペースを開く
2. スペース名をクリック → 「アプリとインテグレーションを管理」
3. 「Webhookを追加」をクリック
4. 名前を入力（例: Zabbix）して「保存」
5. 生成されたWebhook URLをコピーする

**Webhook URL形式**

```
https://chat.googleapis.com/v1/spaces/XXXXXXXXX/messages?key=YYYYYYY&token=ZZZZZZZ
```

---

## 3. 設定方法

設定は3つの方法で行える。優先順位は「環境変数 > config.yaml > {ALERT.SENDTO}」。

### 3.1 方法1: 環境変数（推奨）

`.env` ファイルを作成するか、システム環境変数に設定する。

```bash
# .env ファイルの作成
cp .env.example .env
```

`.env` ファイルの編集:

```bash
GCHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ
ZABBIX_URL=https://zabbix.example.com
LOG_LEVEL=INFO
```

### 3.2 方法2: config.yaml

```bash
cp config/config.yaml.example config/config.yaml
```

`config/config.yaml` を編集:

```yaml
googlechat:
  webhook_url: "https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ"
  timeout: 10
  max_retries: 3
  retry_delay: 1.0

zabbix:
  url: "https://zabbix.example.com"

logging:
  level: INFO
  # file: /var/log/zabbix-googlechat/notify.log  # ファイル出力する場合はコメント解除
```

### 3.3 方法3: {ALERT.SENDTO}

Zabbixのメディアタイプ設定で、ユーザーメディアの「送信先」フィールドにWebhook URLを直接設定する。この方法は他の設定がない場合のフォールバックとして機能する。

---

## 4. Zabbixへのデプロイ

### 4.1 自動インストール（推奨）

`install.sh` を使うと以下を自動的に実行する:

```bash
sudo bash scripts/install.sh
```

- pip install の実行
- AlertScriptsPath の自動検出とスクリプト配置
- `/etc/zabbix-googlechat/config.yaml` の作成

### 4.2 手動インストール

**ステップ 1: パッケージをインストール**

```bash
pip install zabbix-googlechat
```

**ステップ 2: スクリプトを alertscripts に配置**

```bash
# AlertScriptsPath の確認
grep AlertScriptsPath /etc/zabbix/zabbix_server.conf

# スクリプトをコピー
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py
```

**ステップ 3: 設定ファイルの配置**

```bash
sudo mkdir -p /etc/zabbix-googlechat
sudo cp config/config.yaml.example /etc/zabbix-googlechat/config.yaml
# Webhook URL を設定
sudo vi /etc/zabbix-googlechat/config.yaml
```

設定ファイルの探索順序:

1. 環境変数 `ZABBIX_GOOGLECHAT_CONFIG` で明示指定
2. `/etc/zabbix-googlechat/config.yaml`（FHS標準パス）
3. カレントディレクトリの `config/config.yaml`
4. 設定ファイルなし（環境変数のみで動作）

---

## 5. 動作確認

### 5.1 コマンドラインテスト

スクリプトが正しく動作するかをコマンドラインで確認する。

**PROBLEMアラートのテスト:**

```bash
python3 scripts/zabbix_notify.py \
  "" \
  "テスト通知" \
  "ALERT_TYPE=PROBLEM
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_DESCRIPTION=CPU使用率が80%を超えています
TRIGGER_SEVERITY=High
EVENT_ID=12345
EVENT_DATE=2026.03.20
EVENT_TIME=10:00:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=95%"

echo "終了コード: $?"
```

**RECOVERYアラートのテスト:**

```bash
python3 scripts/zabbix_notify.py \
  "" \
  "復旧通知" \
  "ALERT_TYPE=RECOVERY
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_SEVERITY=High
EVENT_ID=12345
EVENT_DATE=2026.03.20
EVENT_TIME=10:00:00
RECOVERY_DATE=2026.03.20
RECOVERY_TIME=10:30:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=45%"

echo "終了コード: $?"
```

**UPDATEアラートのテスト:**

```bash
python3 scripts/zabbix_notify.py \
  "" \
  "確認通知" \
  "ALERT_TYPE=UPDATE
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_SEVERITY=High
EVENT_ID=12345
EVENT_DATE=2026.03.20
EVENT_TIME=10:00:00
ACK_AUTHOR=田中太郎
ACK_MESSAGE=調査中です
ZABBIX_URL=https://zabbix.example.com"

echo "終了コード: $?"
```

### 5.2 終了コードの確認

| コード | 意味 | 対処 |
|---|---|---|
| 0 | 成功 | - |
| 1 | 設定エラー | Webhook URLが設定されているか確認 |
| 2 | 送信エラー | ネットワーク、Webhook URLが正しいか確認 |
| 3 | パースエラー | 引数の形式が正しいか確認 |
| 99 | 予期しないエラー | ログを確認 |

### 5.3 デバッグモードでの実行

詳細なログを出力する場合:

```bash
LOG_LEVEL=DEBUG python3 scripts/zabbix_notify.py "" "テスト" "ALERT_TYPE=PROBLEM
HOST_NAME=test"
```

---

## 6. ログ管理

### 6.1 ログファイルへの出力

`config.yaml` でログファイルを設定する:

```yaml
logging:
  level: INFO
  file: /var/log/zabbix-googlechat/notify.log
```

ログディレクトリの作成と権限設定:

```bash
mkdir -p /var/log/zabbix-googlechat
chown zabbix:zabbix /var/log/zabbix-googlechat
chmod 755 /var/log/zabbix-googlechat
```

### 6.2 ログローテーションの設定

`/etc/logrotate.d/zabbix-googlechat` を作成:

```
/var/log/zabbix-googlechat/notify.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 zabbix zabbix
}
```

---

## 7. トラブルシューティング

### 7.1 よくあるエラー

**設定エラー: Webhook URLが設定されていません**

```
設定エラー: Webhook URLが設定されていません。
以下のいずれかで設定してください:
  1. 環境変数 GCHAT_WEBHOOK_URL
  2. config.yaml の googlechat.webhook_url
  3. {ALERT.SENDTO} に Webhook URLを設定
```

対処: 環境変数 `GCHAT_WEBHOOK_URL` を設定するか、`config/config.yaml` に Webhook URL を記入する。

**送信エラー (HTTP 401)**

```
送信エラー (HTTP 401): Webhookペイロードエラー: HTTP 401
```

対処: Webhook URLのトークンが有効か確認する。Google ChatでWebhookを再作成し、URLを更新する。

**パースエラー: 引数不足**

```
パースエラー: Zabbixスクリプト引数が不足しています: 引数は3つ必要です (SENDTO, SUBJECT, MESSAGE)
```

対処: Zabbixのメディアタイプ設定でパラメータが3つ正しく設定されているか確認する。

### 7.2 接続テスト

Webhook URLへの疎通確認:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"text": "接続テスト"}' \
  "https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ"
```

HTTP 200が返れば正常。
