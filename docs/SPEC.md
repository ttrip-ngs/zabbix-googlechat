# システム設計仕様書: zabbix-googlechat

## 1. 概要

### 1.1 目的

ZabbixのアラートイベントをGoogle Chatに通知する外部スクリプトライブラリ。Zabbixのアクション機能と連携し、Google Chat Card v2形式のリッチカードメッセージで通知を送信する。

### 1.2 対応バージョン

| コンポーネント | バージョン |
|---|---|
| Python | 3.10 / 3.11 / 3.12 / 3.13 |
| Zabbix | 6.0以上 |
| Google Chat Webhook API | v1（Card v2形式） |

### 1.3 機能一覧

- アラートタイプ別通知（PROBLEM / RECOVERY / UPDATE）
- 重要度別絵文字表示
- Google Chat Card v2形式リッチカード通知
- Webhook URL優先順位管理（環境変数 > config.yaml > {ALERT.SENDTO}）
- 指数バックオフによる自動リトライ
- ログファイル出力対応

---

## 2. アーキテクチャ

### 2.1 全体構成

```
Zabbix Server
    │
    │ scripts/zabbix_notify.py を呼び出し
    │ 引数: {ALERT.SENDTO} {ALERT.SUBJECT} {ALERT.MESSAGE}
    ▼
scripts/zabbix_notify.py  ← エントリポイント
    │
    ├─[1] ZabbixParamParser.parse_argv()   ← コマンドライン引数・メッセージ本文解析
    │         src/zabbix_googlechat/parser.py
    │
    ├─[2] NotificationConfig.load()        ← 設定読込（優先順位制御）
    │         src/zabbix_googlechat/config.py
    │
    ├─[3] GoogleChatCardBuilder.build()    ← Card v2ペイロード構築
    │         src/zabbix_googlechat/card_builder.py
    │
    └─[4] GoogleChatWebhookSender.send()   ← Webhook送信（リトライ制御）
              src/zabbix_googlechat/webhook_sender.py
                  │
                  ▼
              Google Chat Webhook API
```

### 2.2 モジュール依存関係

```
scripts/zabbix_notify.py
    ├── zabbix_googlechat.parser        (ZabbixParamParser)
    │       └── zabbix_googlechat.models  (ZabbixEvent, AlertType, Severity)
    │       └── zabbix_googlechat.exceptions (ParseError)
    ├── zabbix_googlechat.config        (NotificationConfig)
    │       └── zabbix_googlechat.exceptions (ConfigurationError)
    ├── zabbix_googlechat.card_builder  (GoogleChatCardBuilder)
    │       └── zabbix_googlechat.models
    └── zabbix_googlechat.webhook_sender (GoogleChatWebhookSender)
            └── zabbix_googlechat.exceptions (WebhookConnectionError, WebhookPayloadError)
```

---

## 3. モジュール仕様

### 3.1 models.py

#### AlertType (Enum)

アラートタイプを表すEnum。Zabbixメッセージ本文の `ALERT_TYPE` キーに対応する。

| 値 | 意味 | 絵文字 |
|---|---|---|
| `PROBLEM` | 障害発生 | 🔴 |
| `RECOVERY` | 復旧 | 🟢 |
| `UPDATE` | 確認・更新 | 🔵 |

未知の値は `UPDATE` にフォールバックする。

#### Severity (Enum)

トリガー重要度を表すEnum。Zabbixの重要度名と1対1対応する。

| 値 | Zabbix表示名 | 絵文字 |
|---|---|---|
| `NOT_CLASSIFIED` | Not classified | ⚪ |
| `INFORMATION` | Information | 🔵 |
| `WARNING` | Warning | 🟡 |
| `AVERAGE` | Average | 🟠 |
| `HIGH` | High | 🔴 |
| `DISASTER` | Disaster | 🔥 |

未知の値は `NOT_CLASSIFIED` にフォールバックする。

#### ZabbixEvent (dataclass)

Zabbixアラートイベントの全情報を保持するデータクラス。

| フィールド | 型 | 説明 | 対応Zabbixマクロ |
|---|---|---|---|
| `alert_type` | AlertType | アラートタイプ | ALERT_TYPE キー |
| `host_name` | str | ホスト名 | {HOST.NAME} |
| `trigger_name` | str | トリガー名 | {TRIGGER.NAME} |
| `trigger_description` | str | トリガー説明 | {TRIGGER.DESCRIPTION} |
| `trigger_severity` | Severity | 重要度 | {TRIGGER.SEVERITY} |
| `event_id` | str | イベントID | {EVENT.ID} |
| `event_date` | str | 発生日付 | {EVENT.DATE} |
| `event_time` | str | 発生時刻 | {EVENT.TIME} |
| `recovery_date` | str | 復旧日付 | {EVENT.RECOVERY.DATE} |
| `recovery_time` | str | 復旧時刻 | {EVENT.RECOVERY.TIME} |
| `ack_message` | str | 確認メッセージ | {ACK.MESSAGE} |
| `ack_author` | str | 確認者 | {USER.FULLNAME} |
| `item_last_value` | str | アイテム最新値 | {ITEM.LASTVALUE} |
| `zabbix_url` | str | Zabbix URL | {$ZABBIX.URL} |
| `webhook_url` | str | Webhook URL | {ALERT.SENDTO} |
| `raw_message` | str | 元メッセージ（デバッグ用） | - |
| `extra` | dict[str, str] | 未知キーの格納先 | - |

プロパティ:
- `event_datetime`: `event_date` と `event_time` を結合した文字列
- `recovery_datetime`: `recovery_date` と `recovery_time` を結合した文字列

### 3.2 parser.py

#### ZabbixParamParser

Zabbixからのコマンドライン引数とメッセージ本文を解析してZabbixEventに変換する。

**メッセージ本文フォーマット**

改行区切りの `KEY=VALUE` 形式。値に `=` が含まれる場合は最初の `=` で分割する。

```
ALERT_TYPE=PROBLEM
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_DESCRIPTION=CPU使用率が80%を超えています
TRIGGER_SEVERITY=High
EVENT_ID=12345
EVENT_DATE=2026.03.20
EVENT_TIME=10:00:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=95%
```

**認識するキー一覧**

| キー名 | 対応フィールド |
|---|---|
| `ALERT_TYPE` | alert_type |
| `HOST_NAME` | host_name |
| `TRIGGER_NAME` | trigger_name |
| `TRIGGER_DESCRIPTION` | trigger_description |
| `TRIGGER_SEVERITY` | trigger_severity |
| `EVENT_ID` | event_id |
| `EVENT_DATE` | event_date |
| `EVENT_TIME` | event_time |
| `RECOVERY_DATE` | recovery_date |
| `RECOVERY_TIME` | recovery_time |
| `ACK_MESSAGE` | ack_message |
| `ACK_AUTHOR` | ack_author |
| `ITEM_LASTVALUE` | item_last_value |
| `ZABBIX_URL` | zabbix_url |

未知キーは `extra` フィールドに格納する。

**parse_argv(argv) の引数仕様**

```
argv[0]: {ALERT.SENDTO}  - Webhook URL（空文字可）
argv[1]: {ALERT.SUBJECT} - アラートタイトル（現在未使用）
argv[2]: {ALERT.MESSAGE} - メッセージ本文（KEY=VALUE形式）
```

引数が3つ未満の場合は `ParseError` を送出する。

### 3.3 config.py

#### NotificationConfig (dataclass)

通知に必要な設定情報を保持するデータクラス。

**設定フィールド**

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `webhook_url` | str | "" | Google Chat Webhook URL（必須） |
| `timeout` | int | 10 | HTTPタイムアウト（秒） |
| `max_retries` | int | 3 | 最大リトライ回数 |
| `retry_delay` | float | 1.0 | リトライ間隔基準値（秒） |
| `zabbix_url` | str | "" | ZabbixサーバーURL |
| `log_level` | str | "INFO" | ログレベル |
| `log_file` | str | "" | ログファイルパス（空=標準エラー出力） |

**設定優先順位（高→低）**

```
1. 環境変数 (GCHAT_WEBHOOK_URL 等)
2. config/config.yaml
3. {ALERT.SENDTO} 引数
```

**クラスメソッド**

| メソッド | 説明 |
|---|---|
| `load(yaml_path, env_file, alert_sendto)` | 優先順位制御を含む統合ローダー |
| `from_env(env_file)` | 環境変数のみから読込 |
| `from_yaml(path)` | YAMLファイルのみから読込 |
| `validate()` | 設定値の妥当性検証 |

**validate() の検証内容**

- `webhook_url` が空でないこと
- `webhook_url` が `https://` で始まること
- `timeout` が正の整数であること
- `max_retries` が0以上であること
- `log_level` が有効な値（DEBUG/INFO/WARNING/ERROR/CRITICAL）であること

### 3.4 card_builder.py

#### GoogleChatCardBuilder

ZabbixEventからGoogle Chat Card v2形式のJSONペイロードを構築する。

**カード構造**

```
┌────────────────────────────────────────────┐
│ ヘッダー                                    │
│   タイトル:  🔴 [PROBLEM] ホスト名          │
│   サブタイトル: トリガー名                   │
├────────────────────────────────────────────┤
│ 問題情報セクション                          │
│   🖥️ ホスト: {host_name}                   │
│   ⚠️ 重要度: 🔴 High                       │
│   📝 詳細: {trigger_description}           │（あれば）
│   📊 現在値: {item_last_value}             │（あれば）
├────────────────────────────────────────────┤
│ イベント情報セクション                      │
│   🕐 発生日時: {event_datetime}            │（あれば）
│   🆔 イベントID: {event_id}               │（あれば）
│   🟢 復旧日時: {recovery_datetime}        │（RECOVERY時）
│   👤 確認者: {ack_author}                 │（UPDATE時）
│   💬 確認メッセージ: {ack_message}        │（UPDATE時）
├────────────────────────────────────────────┤
│ アクションセクション                        │
│   [Zabbixで確認する →]                     │（zabbix_urlあれば）
└────────────────────────────────────────────┘
```

**Zabbixリンクの生成規則**

- `event_id` がある場合: `{zabbix_url}/tr_events.php?triggerid=&eventid={event_id}`
- `event_id` がない場合: `{zabbix_url}` をそのまま使用

### 3.5 webhook_sender.py

#### GoogleChatWebhookSender

Google Chat Webhook APIへのHTTP POST送信クライアント。

**リトライ戦略**

| 条件 | 対応 |
|---|---|
| HTTP 429, 500, 502, 503, 504 | リトライ対象 |
| HTTP 400, 401, 403, 404 | 即時 `WebhookPayloadError` 送出 |
| `ConnectionError`, `Timeout` | リトライ対象 |
| その他の `RequestException` | 即時 `WebhookConnectionError` 送出 |

**バックオフ計算式**

```
待機時間 = retry_delay × 2^(retry_count - 1)

例（retry_delay=1.0, max_retries=3）:
  1回目リトライ: 1.0秒
  2回目リトライ: 2.0秒
  3回目リトライ: 4.0秒
```

`max_retries` 回のリトライ後も失敗した場合は `WebhookConnectionError` を送出する。

#### WebhookResponse (dataclass)

| フィールド | 型 | 説明 |
|---|---|---|
| `success` | bool | 送信成功フラグ |
| `status_code` | int | HTTPステータスコード |
| `body` | str | レスポンスボディ |
| `retry_count` | int | 実際のリトライ回数 |
| `elapsed_ms` | float | 送信所要時間（ms） |
| `error_message` | str | エラーメッセージ（失敗時） |

### 3.6 exceptions.py

#### 例外クラス階層

```
ZabbixGoogleChatError (基底例外)
    ├── ConfigurationError      - 設定エラー（必須設定未定義、不正値）
    ├── ParseError              - パースエラー（引数不足、フォーマット不正）
    ├── WebhookConnectionError  - 接続エラー（ネットワーク障害、リトライ上限超過）
    │       属性: retry_count (int)
    └── WebhookPayloadError     - ペイロードエラー（400 Bad Request等）
            属性: status_code (int), response_body (str)
```

---

## 4. エントリポイント仕様

### 4.1 呼び出し形式

```
zabbix_notify.py <ALERT.SENDTO> <ALERT.SUBJECT> <ALERT.MESSAGE>
```

### 4.2 処理フロー

```
1. コマンドライン引数解析 (ZabbixParamParser.parse_argv)
   ├── 失敗 → stderr出力 → 終了コード3
   └── 成功 → ZabbixEvent生成

2. 設定読込 (NotificationConfig.load + validate)
   ├── 失敗 → stderr出力 → 終了コード1
   └── 成功 → NotificationConfig生成

3. ログ設定再適用 (setup_logging)

4. Card v2ペイロード構築 (GoogleChatCardBuilder.build)

5. Webhook送信 (GoogleChatWebhookSender.send)
   ├── WebhookPayloadError → stderr出力 → 終了コード2
   ├── WebhookConnectionError → stderr出力 → 終了コード2
   ├── その他例外 → stderr出力 → 終了コード99
   └── 成功 → 終了コード0
```

### 4.3 終了コード

| コード | 定数名 | 意味 |
|---|---|---|
| 0 | EXIT_SUCCESS | 成功 |
| 1 | EXIT_CONFIG_ERROR | 設定エラー（ConfigurationError） |
| 2 | EXIT_SEND_ERROR | 送信エラー（WebhookConnectionError / WebhookPayloadError） |
| 3 | EXIT_PARSE_ERROR | パースエラー（ParseError） |
| 99 | EXIT_UNEXPECTED_ERROR | 予期しないエラー |

### 4.4 ログ出力

- 出力先: 標準エラー出力（`sys.stderr`）、オプションでファイル追記
- フォーマット: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- レベル: `NotificationConfig.log_level` に従う（デフォルト: INFO）

---

## 5. Google Chat Card v2 ペイロード形式

### 5.1 送信ペイロードの構造

```json
{
  "cardsV2": [
    {
      "cardId": "zabbix-alert-{event_id}",
      "card": {
        "header": {
          "title": "🔴 [PROBLEM] web01.example.com",
          "subtitle": "CPU使用率が高い"
        },
        "sections": [
          {
            "header": "問題情報",
            "widgets": [
              {
                "decoratedText": {
                  "topLabel": "ホスト",
                  "text": "🖥️ web01.example.com"
                }
              },
              ...
            ]
          },
          ...
        ]
      }
    }
  ]
}
```

### 5.2 Webhook URL形式

```
https://chat.googleapis.com/v1/spaces/{SPACE_ID}/messages?key={KEY}&token={TOKEN}
```

---

## 6. 設定ファイル仕様

### 6.1 config.yaml 構造

```yaml
googlechat:
  webhook_url: "https://chat.googleapis.com/v1/spaces/..."
  timeout: 10          # HTTPタイムアウト（秒）
  max_retries: 3       # 最大リトライ回数
  retry_delay: 1.0     # リトライ間隔基準値（秒）

zabbix:
  url: "https://zabbix.example.com"

logging:
  level: INFO          # DEBUG / INFO / WARNING / ERROR / CRITICAL
  file: ""             # ログファイルパス（空=標準エラー出力）
```

### 6.2 環境変数一覧

| 変数名 | 対応フィールド | デフォルト | 必須 |
|---|---|---|---|
| `GCHAT_WEBHOOK_URL` | webhook_url | - | 必須 |
| `ZABBIX_URL` | zabbix_url | "" | 任意 |
| `GCHAT_TIMEOUT` | timeout | 10 | 任意 |
| `GCHAT_MAX_RETRIES` | max_retries | 3 | 任意 |
| `LOG_LEVEL` | log_level | INFO | 任意 |
| `LOG_FILE` | log_file | "" | 任意 |

---

## 7. 依存ライブラリ

| ライブラリ | バージョン | 用途 |
|---|---|---|
| `requests` | >=2.28.0 | HTTP Webhook送信 |
| `pyyaml` | >=6.0.0 | config.yaml解析 |
| `python-dotenv` | >=1.0.0 | .envファイル読込 |

開発用:

| ライブラリ | 用途 |
|---|---|
| `pytest` | テスト実行 |
| `pytest-cov` | カバレッジ計測 |
| `pytest-mock` | モック |
| `responses` | HTTPモック |
| `ruff` | Lint・フォーマット |
| `mypy` | 型チェック |
| `bandit` | セキュリティ静的解析 |
| `safety` | 依存ライブラリ脆弱性チェック |
