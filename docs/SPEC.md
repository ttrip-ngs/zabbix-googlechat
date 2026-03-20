# 仕様書: zabbix-googlechat

## 概要

ZabbixのアラートをGoogle Chatに送信する外部スクリプトライブラリ。
Google Chat Card v2形式のリッチカード通知を実現する。

## アーキテクチャ

```
scripts/zabbix_notify.py (エントリポイント)
    ├── ZabbixParamParser    (parser.py)    - パラメータ解析
    ├── NotificationConfig   (config.py)    - 設定管理
    ├── GoogleChatCardBuilder (card_builder.py) - カード生成
    └── GoogleChatWebhookSender (webhook_sender.py) - Webhook送信
```

## モジュール仕様

### models.py

#### AlertType (Enum)

| 値 | 説明 |
|---|---|
| PROBLEM | 障害発生 |
| RECOVERY | 復旧 |
| UPDATE | 確認・更新 |

#### Severity (Enum)

| 値 | Zabbix重要度 | 絵文字 |
|---|---|---|
| Not classified | 未分類 | ⚪ |
| Information | 情報 | 🔵 |
| Warning | 警告 | 🟡 |
| Average | 軽度障害 | 🟠 |
| High | 重大障害 | 🔴 |
| Disaster | 致命的障害 | 🔥 |

#### ZabbixEvent (dataclass)

Zabbixイベントの全パラメータを保持するデータクラス。

### parser.py

#### ZabbixParamParser

メッセージ本文フォーマット（改行区切り key=value）:
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

不明なアラートタイプは UPDATE、不明な重要度は NOT_CLASSIFIED にフォールバック。

### config.py

#### 設定優先順位（高→低）

1. 環境変数 (`GCHAT_WEBHOOK_URL` 等)
2. `config/config.yaml`
3. `{ALERT.SENDTO}` 引数

#### 環境変数一覧

| 変数名 | 説明 | デフォルト |
|---|---|---|
| GCHAT_WEBHOOK_URL | Webhook URL | (必須) |
| ZABBIX_URL | Zabbix URL | "" |
| GCHAT_TIMEOUT | タイムアウト(秒) | 10 |
| GCHAT_MAX_RETRIES | 最大リトライ回数 | 3 |
| LOG_LEVEL | ログレベル | INFO |
| LOG_FILE | ログファイルパス | "" (stdout) |

### webhook_sender.py

#### リトライ戦略

- 対象ステータスコード: 429, 500, 502, 503, 504
- 非対象（即時例外）: 400, 401, 403, 404
- バックオフ: `retry_delay * 2^(retry_count-1)` 秒
- 最大リトライ: `max_retries` 回（デフォルト3回）

## 終了コード

| コード | 意味 |
|---|---|
| 0 | 成功 |
| 1 | 設定エラー |
| 2 | 送信エラー |
| 3 | パースエラー |
| 99 | 予期しないエラー |
