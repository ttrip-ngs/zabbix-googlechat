# クイックスタートガイド

Zabbixサーバーに zabbix-googlechat を導入してGoogle Chat通知を有効にする手順。

## 前提条件

- Python 3.9 以上がインストール済みであること
- pip が使用可能であること
- Google Chat Webhook URL を取得済みであること（取得方法は後述）

Python バージョンの確認:

```bash
python3 --version
# Python 3.9.x 以上であること
```

---

## Google Chat Webhook URL の取得

1. Google Chat でWebhookを設定したいスペースを開く
2. スペース名をクリック → 「アプリとインテグレーションを管理」
3. 「Webhookを追加」をクリック
4. 名前を入力（例: Zabbix）して「保存」
5. 生成された Webhook URL をコピーする

URL の形式:

```
https://chat.googleapis.com/v1/spaces/XXXXXXXXX/messages?key=YYYYYYY&token=ZZZZZZZ
```

---

## 導入手順

### 方法1: install.sh を使った自動インストール（推奨）

リポジトリを取得してインストールスクリプトを実行する。

```bash
# リポジトリを取得
git clone https://github.com/your-org/zabbix-googlechat.git
cd zabbix-googlechat

# インストール（root 権限が必要）
sudo bash scripts/install.sh
```

スクリプトが以下を自動的に行う:

- Python バージョンの確認
- `pip install` の実行
- `AlertScriptsPath` の自動検出と `zabbix_notify.py` の配置
- `/etc/zabbix-googlechat/config.yaml` の作成

### 方法2: 手動インストール

**ステップ 1: パッケージをインストール**

```bash
pip install zabbix-googlechat
# または、ローカルリポジトリから
pip install /path/to/zabbix-googlechat
```

**ステップ 2: スクリプトを alertscripts に配置**

```bash
# AlertScriptsPath の確認
grep AlertScriptsPath /etc/zabbix/zabbix_server.conf
# 例: AlertScriptsPath=/usr/lib/zabbix/alertscripts

# スクリプトをコピー
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py
```

**ステップ 3: 設定ファイルを作成**

```bash
sudo mkdir -p /etc/zabbix-googlechat
sudo cp config/config.yaml.example /etc/zabbix-googlechat/config.yaml
sudo vi /etc/zabbix-googlechat/config.yaml
```

`config.yaml` の最低限の設定:

```yaml
googlechat:
  webhook_url: "https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ"

zabbix:
  url: "https://zabbix.example.com"  # ZabbixサーバーのURL（省略可）
```

---

## 動作確認

インストール後、以下のコマンドで動作を確認する。

```bash
sudo -u zabbix python3 /usr/lib/zabbix/alertscripts/zabbix_notify.py \
  "" \
  "テスト通知" \
  "ALERT_TYPE=PROBLEM
HOST_NAME=test-server
TRIGGER_NAME=テストアラート
TRIGGER_SEVERITY=High
EVENT_ID=99999
EVENT_DATE=2026.01.01
EVENT_TIME=00:00:00"

echo "終了コード: $?"
```

終了コード 0 が返り、Google Chat にカードが届けば成功。

### 環境変数のみで動作確認（config.yaml 不要）

```bash
GCHAT_WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ" \
  python3 /usr/lib/zabbix/alertscripts/zabbix_notify.py \
  "" \
  "テスト" \
  "ALERT_TYPE=PROBLEM
HOST_NAME=test
TRIGGER_NAME=テスト
TRIGGER_SEVERITY=High
EVENT_ID=1
EVENT_DATE=2026.01.01
EVENT_TIME=00:00:00"
```

---

## Zabbix の設定

### メディアタイプの作成

Zabbix 管理画面 > 通知 > メディアタイプ > メディアタイプの作成

| 項目 | 設定値 |
|---|---|
| 名前 | Google Chat |
| タイプ | スクリプト |
| スクリプト名 | `zabbix_notify.py` |

スクリプトパラメータ（順番通りに追加）:

| 順番 | 値 |
|---|---|
| 1 | `{ALERT.SENDTO}` |
| 2 | `{ALERT.SUBJECT}` |
| 3 | `{ALERT.MESSAGE}` |

### アクションのメッセージ本文設定

PROBLEM 通知のメッセージ本文:

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

RECOVERY 通知のメッセージ本文:

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

UPDATE 通知のメッセージ本文:

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

詳細な Zabbix 設定手順は [ZABBIX_SETUP.md](ZABBIX_SETUP.md) を参照。

---

## トラブルシューティング

### 終了コードの意味

| コード | 原因 | 対処 |
|---|---|---|
| 0 | 成功 | - |
| 1 | 設定エラー | Webhook URL が設定されているか確認 |
| 2 | 送信エラー | ネットワーク、Webhook URL の有効性を確認 |
| 3 | パースエラー | Zabbix メディアタイプのパラメータ設定を確認 |
| 99 | 予期しないエラー | ログを確認 |

### よくあるエラー

**Webhook URL が設定されていません**

```
設定エラー: Webhook URLが設定されていません。
```

対処: 以下のいずれかで Webhook URL を設定する。

- 環境変数: `export GCHAT_WEBHOOK_URL="https://..."`
- 設定ファイル: `/etc/zabbix-googlechat/config.yaml` の `googlechat.webhook_url`
- Zabbix メディアタイプのユーザーメディア「送信先」フィールド

**パースエラー: 引数不足**

```
パースエラー: Zabbixスクリプト引数が不足しています
```

対処: Zabbix のメディアタイプ設定でスクリプトパラメータが3つ設定されているか確認する。

**デバッグログの有効化**

詳細ログを出力する場合:

```bash
LOG_LEVEL=DEBUG sudo -u zabbix python3 /usr/lib/zabbix/alertscripts/zabbix_notify.py ...
```

または `/etc/zabbix-googlechat/config.yaml` で:

```yaml
logging:
  level: DEBUG
  file: /var/log/zabbix-googlechat/notify.log
```
