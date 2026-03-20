# 001 初期実装

日付: 2026-03-11

## 実施内容

Zabbix Google Chat 通知ライブラリの初期実装。

## 主要ファイル

- `src/zabbix_googlechat/models.py`: AlertType/Severity Enum、ZabbixEvent dataclass
- `src/zabbix_googlechat/exceptions.py`: カスタム例外クラス
- `src/zabbix_googlechat/parser.py`: ZabbixParamParser（key=value形式パース）
- `src/zabbix_googlechat/config.py`: NotificationConfig（優先順位: 環境変数 > yaml > ALERT.SENDTO）
- `src/zabbix_googlechat/card_builder.py`: GoogleChatCardBuilder（Card v2形式）
- `src/zabbix_googlechat/webhook_sender.py`: GoogleChatWebhookSender（指数バックオフリトライ）
- `scripts/zabbix_notify.py`: エントリポイント（終了コード: 0/1/2/3/99）

## 注意事項

- Google Chat Card v2では絵文字はtextに直接埋め込む形式を採用（外部URL不要）
- Webhook URL優先順位: 環境変数GCHAT_WEBHOOK_URL > config.yaml > {ALERT.SENDTO}
- リトライ対象: 429/500/502/503/504、非対象: 400/401/403/404
- Zabbixメッセージ本文は改行区切りのkey=value形式
