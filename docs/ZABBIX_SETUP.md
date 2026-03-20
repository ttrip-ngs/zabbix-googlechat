# Zabbix設定ガイド

## スクリプト配置

Zabbixのexternalscriptsディレクトリにスクリプトを配置する。

```bash
# スクリプトのコピー
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py

# 依存ライブラリのインストール
pip install requests pyyaml python-dotenv
```

## メディアタイプ設定

Zabbix管理画面でメディアタイプを作成する。

### 設定値

- **名前**: Google Chat
- **タイプ**: スクリプト
- **スクリプト名**: `zabbix_notify.py`

### スクリプトパラメータ

| 順番 | パラメータ | 説明 |
|---|---|---|
| 1 | `{ALERT.SENDTO}` | Webhook URL（空にすると設定ファイル優先） |
| 2 | `{ALERT.SUBJECT}` | アラートタイトル（現在は未使用） |
| 3 | `{ALERT.MESSAGE}` | アラートメッセージ本文 |

## アクションテンプレート

### PROBLEM テンプレート（メッセージ本文）

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

### RECOVERY テンプレート（メッセージ本文）

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

### UPDATE テンプレート（メッセージ本文）

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

## ユーザーメディアの設定

Zabbixユーザーのメディア設定:
- **タイプ**: Google Chat
- **送信先 (Send To)**: 空文字（config.yamlでWebhook URLを管理）またはWebhook URL

## グローバルマクロの設定

Zabbix管理画面 > 管理 > 一般 > マクロ:
- `{$ZABBIX.URL}` = `https://zabbix.example.com`（自環境のZabbix URL）

## 動作確認

```bash
# テスト送信
python /usr/lib/zabbix/alertscripts/zabbix_notify.py \
  "" \
  "テスト通知" \
  "ALERT_TYPE=PROBLEM
HOST_NAME=test-server
TRIGGER_NAME=テストアラート
TRIGGER_SEVERITY=Warning
EVENT_ID=99999
EVENT_DATE=2026.03.11
EVENT_TIME=12:00:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=test"

echo "終了コード: $?"
```
