# zabbix-googlechat

ZabbixのアラートをGoogle Chatに送信する外部スクリプトライブラリ。

Google Chat Card v2形式のリッチなカードメッセージで、アラートの重要度や種別を視覚的に判別しやすい通知を実現する。

## クイックスタート（Zabbixサーバー運用者向け）

```bash
# 1. パッケージをインストール（alertscripts コマンドが使えるようになる）
pip install zabbix-googlechat

# 2. スクリプトを alertscripts に配置
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py

# 3. Webhook URL を設定
sudo mkdir -p /etc/zabbix-googlechat
echo 'googlechat:\n  webhook_url: "https://chat.googleapis.com/..."' \
  | sudo tee /etc/zabbix-googlechat/config.yaml
```

または `install.sh` で一括インストール:

```bash
sudo bash scripts/install.sh
```

詳細な導入手順は [docs/QUICKSTART.md](docs/QUICKSTART.md) を参照。

---

## 機能

- アラートタイプ別の絵文字表示 (PROBLEM: 🔴, RECOVERY: 🟢, UPDATE: 🔵)
- 重要度別の絵文字表示 (Disaster: 🔥, High: 🔴, Warning: 🟡, etc.)
- Google Chat Card v2 形式のリッチカード通知
- Webhook URL の優先順位管理（環境変数 > config.yaml > {ALERT.SENDTO}）
- 自動リトライ（指数バックオフ）
- Python 3.10 / 3.11 / 3.12 / 3.13 対応

## 動作要件

- Python 3.10 以上
- Zabbix 6.0 以上
- Google Chat Webhook URL

## インストール

本番運用:

```bash
pip install zabbix-googlechat
```

開発環境:

```bash
pip install -e ".[dev]"
pre-commit install
```

## 設定

### 方法 1: 環境変数

```bash
export GCHAT_WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/..."
export ZABBIX_URL="https://zabbix.example.com"
```

### 方法 2: 設定ファイル

```bash
cp config/config.yaml.example config/config.yaml
# config/config.yaml を編集
```

### 方法 3: {ALERT.SENDTO}

ZabbixメディアタイプのSend toフィールドにWebhook URLを設定する。

## Zabbix設定

詳細は [docs/ZABBIX_SETUP.md](docs/ZABBIX_SETUP.md) を参照。

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 導入クイックスタート（Zabbixサーバー運用者向け） |
| [docs/USAGE.md](docs/USAGE.md) | インストール・設定・動作確認・トラブルシューティング |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | 全設定項目のリファレンス |
| [docs/ZABBIX_SETUP.md](docs/ZABBIX_SETUP.md) | Zabbixメディアタイプ・アクションの設定手順 |
| [docs/SPEC.md](docs/SPEC.md) | システム設計仕様書（アーキテクチャ・モジュール仕様） |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 開発環境構築・テスト・Git運用ガイド |

### スクリプト配置

```bash
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py
```

### メディアタイプ設定

- スクリプト名: `zabbix_notify.py`
- パラメータ:
  1. `{ALERT.SENDTO}` (Webhook URLまたは空文字)
  2. `{ALERT.SUBJECT}`
  3. `{ALERT.MESSAGE}`

## 使用方法

### 手動テスト

```bash
python scripts/zabbix_notify.py "" "test" "ALERT_TYPE=PROBLEM
HOST_NAME=test-server
TRIGGER_NAME=CPU使用率が高い
TRIGGER_SEVERITY=High
EVENT_ID=12345
EVENT_DATE=2026.03.11
EVENT_TIME=18:00:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=95%"
```

## 開発

### テスト実行

```bash
python -m pytest tests/unit/ -v
python -m pytest tests/unit/ --cov=zabbix_googlechat --cov-report=term-missing
```

### 品質チェック

```bash
python -m ruff check .
python -m ruff format .
python -m mypy src
python -m bandit -r src -ll
```

## ライセンス

MIT
