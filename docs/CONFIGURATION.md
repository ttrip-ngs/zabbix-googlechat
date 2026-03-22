# 設定リファレンス

## 1. 設定方法の優先順位

設定は以下の優先順位で適用される。高い優先度の設定が低い優先度の設定を上書きする。

```
優先度1 (最高): 環境変数
優先度2:        config/config.yaml
優先度3 (最低): {ALERT.SENDTO} 引数
```

例: 環境変数 `GCHAT_WEBHOOK_URL` が設定されていれば、`config.yaml` の `webhook_url` は無視される。

---

## 2. 環境変数

`.env` ファイルに記述するか、システム環境変数として設定する。

### 2.1 必須設定

| 変数名 | 説明 | 例 |
|---|---|---|
| `GCHAT_WEBHOOK_URL` | Google Chat Webhook URL | `https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ` |

### 2.2 任意設定

| 変数名 | 説明 | デフォルト | 例 |
|---|---|---|---|
| `ZABBIX_URL` | ZabbixサーバーのベースURL | "" | `https://zabbix.example.com` |
| `GCHAT_TIMEOUT` | HTTPリクエストタイムアウト（秒） | 10 | `30` |
| `GCHAT_MAX_RETRIES` | 送信失敗時の最大リトライ回数 | 3 | `5` |
| `LOG_LEVEL` | ログ出力レベル | INFO | `DEBUG` |
| `LOG_FILE` | ログファイルの出力先パス | "" | `/var/log/zabbix-googlechat/notify.log` |

### 2.3 .env ファイルのサンプル

```bash
# Google Chat設定
GCHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/XXXXXXXXX/messages?key=YYYYYYY&token=ZZZZZZZ

# Zabbix設定
ZABBIX_URL=https://zabbix.example.com

# タイムアウト・リトライ設定
GCHAT_TIMEOUT=10
GCHAT_MAX_RETRIES=3

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=/var/log/zabbix-googlechat/notify.log
```

---

## 3. config.yaml

`config/config.yaml` に配置する。スクリプトは起動時に自動検出する。

### 3.1 全設定項目

```yaml
googlechat:
  # Google Chat Webhook URL（必須）
  # 環境変数 GCHAT_WEBHOOK_URL で上書き可能
  webhook_url: "https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ"

  # HTTPリクエストタイムアウト（秒）
  # 環境変数 GCHAT_TIMEOUT で上書き可能
  timeout: 10

  # 送信失敗時の最大リトライ回数
  # 0を指定するとリトライなし
  # 環境変数 GCHAT_MAX_RETRIES で上書き可能
  max_retries: 3

  # リトライ間隔の基準値（秒）
  # 実際の待機時間: retry_delay × 2^(リトライ回数-1)
  # 例: retry_delay=1.0 → 1秒, 2秒, 4秒...
  retry_delay: 1.0

zabbix:
  # ZabbixサーバーのベースURL
  # カードの「Zabbixで確認する」ボタンのリンク先に使用
  # 環境変数 ZABBIX_URL で上書き可能
  url: "https://zabbix.example.com"

logging:
  # ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
  # 環境変数 LOG_LEVEL で上書き可能
  level: INFO

  # ログファイルの出力先（省略時は標準エラー出力のみ）
  # 環境変数 LOG_FILE で上書き可能
  # file: /var/log/zabbix-googlechat/notify.log
```

### 3.2 各設定項目の説明

#### googlechat.webhook_url

Google ChatスペースのWebhook URL。Google Chat管理画面から取得する。

- 必須項目
- `https://` で始まる必要がある
- 秘密情報のため `.gitignore` で管理対象外にすること

#### googlechat.timeout

Webhook APIへのHTTPリクエストのタイムアウト秒数。

- デフォルト: 10秒
- ネットワーク環境に応じて調整する

#### googlechat.max_retries

送信失敗時のリトライ回数上限。

- デフォルト: 3回
- 0を設定するとリトライなし（即時エラー）
- リトライ対象: HTTP 429, 500, 502, 503, 504, ネットワーク障害
- リトライ非対象: HTTP 400, 401, 403, 404（即時エラー）

#### googlechat.retry_delay

指数バックオフのリトライ間隔基準値（秒）。

- デフォルト: 1.0秒
- 実際の待機時間: `retry_delay × 2^(リトライ回数-1)`
  - 1回目: 1.0秒
  - 2回目: 2.0秒
  - 3回目: 4.0秒

#### zabbix.url

ZabbixサーバーのベースURL。カード内の「Zabbixで確認する」ボタンのリンク先として使用する。

- 省略時はリンクボタンが表示されない
- メッセージ本文の `ZABBIX_URL` キーでも指定可能（そちらが優先される）

#### logging.level

ログ出力の詳細度。

| レベル | 出力内容 |
|---|---|
| DEBUG | 全ての処理ログ（パース結果、カード構造等） |
| INFO | 通常の処理ログ（送信成功、リトライ情報等） |
| WARNING | 警告（無効な設定値、リトライ発生等） |
| ERROR | エラー（送信失敗等） |
| CRITICAL | 致命的エラー |

#### logging.file

ログを書き込むファイルのパス。

- 省略または空文字の場合は標準エラー出力のみ
- ファイルとstderrの両方に同時出力される
- ファイルを開けない場合は警告を出力してstderrのみで継続

---

## 4. Zabbixメッセージ本文のパラメータ

Zabbixアクションの「メッセージ本文」に設定するパラメータ一覧。改行区切りの `KEY=VALUE` 形式で指定する。

### 4.1 PROBLEM テンプレート

```
ALERT_TYPE=PROBLEM
HOST_NAME={HOST.NAME}
TRIGGER_NAME={TRIGGER.NAME}
TRIGGER_DESCRIPTION={TRIGGER.DESCRIPTION}
TRIGGER_SEVERITY={TRIGGER.SEVERITY}
EVENT_ID={EVENT.ID}
EVENT_DATE={EVENT.DATE}
EVENT_TIME={EVENT.TIME}
ZABBIX_URL={$ZABBIX.URL}
ITEM_LASTVALUE={ITEM.LASTVALUE}
```

### 4.2 RECOVERY テンプレート

```
ALERT_TYPE=RECOVERY
HOST_NAME={HOST.NAME}
TRIGGER_NAME={TRIGGER.NAME}
TRIGGER_DESCRIPTION={TRIGGER.DESCRIPTION}
TRIGGER_SEVERITY={TRIGGER.SEVERITY}
EVENT_ID={EVENT.ID}
EVENT_DATE={EVENT.DATE}
EVENT_TIME={EVENT.TIME}
RECOVERY_DATE={EVENT.RECOVERY.DATE}
RECOVERY_TIME={EVENT.RECOVERY.TIME}
ZABBIX_URL={$ZABBIX.URL}
ITEM_LASTVALUE={ITEM.LASTVALUE}
```

### 4.3 UPDATE テンプレート

```
ALERT_TYPE=UPDATE
HOST_NAME={HOST.NAME}
TRIGGER_NAME={TRIGGER.NAME}
TRIGGER_DESCRIPTION={TRIGGER.DESCRIPTION}
TRIGGER_SEVERITY={TRIGGER.SEVERITY}
EVENT_ID={EVENT.ID}
EVENT_DATE={EVENT.DATE}
EVENT_TIME={EVENT.TIME}
ACK_AUTHOR={USER.FULLNAME}
ACK_MESSAGE={ACK.MESSAGE}
ZABBIX_URL={$ZABBIX.URL}
ITEM_LASTVALUE={ITEM.LASTVALUE}
```

### 4.4 パラメータ詳細

| キー | 対応Zabbixマクロ | 説明 |
|---|---|---|
| `ALERT_TYPE` | 固定値 | PROBLEM / RECOVERY / UPDATE のいずれか |
| `HOST_NAME` | {HOST.NAME} | アラート発生ホスト名 |
| `TRIGGER_NAME` | {TRIGGER.NAME} | トリガー名 |
| `TRIGGER_DESCRIPTION` | {TRIGGER.DESCRIPTION} | トリガーの説明（省略可） |
| `TRIGGER_SEVERITY` | {TRIGGER.SEVERITY} | 重要度（Not classified / Information / Warning / Average / High / Disaster） |
| `EVENT_ID` | {EVENT.ID} | イベントID（Zabbixリンク生成に使用） |
| `EVENT_DATE` | {EVENT.DATE} | 発生日付 |
| `EVENT_TIME` | {EVENT.TIME} | 発生時刻 |
| `RECOVERY_DATE` | {EVENT.RECOVERY.DATE} | 復旧日付（RECOVERYのみ） |
| `RECOVERY_TIME` | {EVENT.RECOVERY.TIME} | 復旧時刻（RECOVERYのみ） |
| `ACK_AUTHOR` | {USER.FULLNAME} | 確認者名（UPDATEのみ） |
| `ACK_MESSAGE` | {ACK.MESSAGE} | 確認コメント（UPDATEのみ） |
| `ZABBIX_URL` | {$ZABBIX.URL} | ZabbixサーバーURL（グローバルマクロ） |
| `ITEM_LASTVALUE` | {ITEM.LASTVALUE} | 監視アイテムの最新値 |
