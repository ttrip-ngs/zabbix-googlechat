# Zabbix設定ガイド

## 1. 前提条件

- Zabbix 6.0以上
- Zabbixサーバーに Python 3.10以上がインストールされていること
- Google Chat Webhook URLを取得済みであること（取得方法は [USAGE.md](USAGE.md) を参照）

---

## 2. スクリプトの配置

### 2.1 alertscriptsディレクトリの確認

Zabbixの外部スクリプトディレクトリを確認する。デフォルトは `/usr/lib/zabbix/alertscripts`。

```bash
grep AlertScriptsPath /etc/zabbix/zabbix_server.conf
# 例: AlertScriptsPath=/usr/lib/zabbix/alertscripts
```

### 2.2 スクリプトのコピー

```bash
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py
```

### 2.3 依存ライブラリのインストール

```bash
pip3 install requests pyyaml python-dotenv
```

システムのPythonに直接インストールできない場合は仮想環境を使用する:

```bash
python3 -m venv /opt/zabbix-googlechat/venv
/opt/zabbix-googlechat/venv/bin/pip install requests pyyaml python-dotenv
```

仮想環境を使用する場合、スクリプト1行目のshebangを変更する:

```python
#!/opt/zabbix-googlechat/venv/bin/python3
```

### 2.4 設定ファイルの配置

```bash
# スクリプトのひとつ上のディレクトリにconfigディレクトリを作成
mkdir -p /usr/lib/zabbix/config
cp config/config.yaml.example /usr/lib/zabbix/config/config.yaml

# Webhook URLを設定
vi /usr/lib/zabbix/config/config.yaml
```

スクリプトは `{スクリプトのディレクトリ}/../config/config.yaml` を自動検出する。

---

## 3. Zabbixメディアタイプの設定

Zabbix管理画面 > 通知 > メディアタイプ > メディアタイプの作成

### 3.1 基本設定

| 項目 | 設定値 |
|---|---|
| 名前 | Google Chat |
| タイプ | スクリプト |
| スクリプト名 | `zabbix_notify.py` |

### 3.2 スクリプトパラメータ

「スクリプトパラメータ」に以下を順番通りに追加する。

| 順番 | 値 | 説明 |
|---|---|---|
| 1 | `{ALERT.SENDTO}` | 送信先（Webhook URLまたは空文字） |
| 2 | `{ALERT.SUBJECT}` | アラートタイトル（現在未使用） |
| 3 | `{ALERT.MESSAGE}` | アラートメッセージ本文 |

### 3.3 メディアオプション（任意）

| 項目 | 推奨設定 |
|---|---|
| 有効な時間帯 | 1-7,00:00-24:00（24時間）|
| 重要度 | 全てチェック |
| 有効 | チェック |

---

## 4. アクションの設定

Zabbix管理画面 > 通知 > アクション > トリガーアクション

### 4.1 アクションの作成

「アクションの作成」から新しいアクションを作成する。

**アクション基本設定**

| 項目 | 設定値 |
|---|---|
| 名前 | Google Chat通知 |
| 有効 | チェック |

### 4.2 操作（PROBLEM通知）

「操作」タブ → 「操作の追加」

| 項目 | 設定値 |
|---|---|
| 操作タイプ | メッセージの送信 |
| ユーザーへの送信 または グループへの送信 | 通知対象ユーザー/グループ |
| メディアのみによる送信 | Google Chat |

**メッセージ本文（PROBLEM）:**

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

### 4.3 リカバリ操作（RECOVERY通知）

「リカバリ操作」タブ → 「操作の追加」

| 項目 | 設定値 |
|---|---|
| 操作タイプ | メッセージの送信 |
| ユーザーへの送信 または グループへの送信 | 通知対象ユーザー/グループ |
| メディアのみによる送信 | Google Chat |

**メッセージ本文（RECOVERY）:**

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

### 4.4 更新操作（UPDATE通知）

「更新操作」タブ → 「操作の追加」

| 項目 | 設定値 |
|---|---|
| 操作タイプ | メッセージの送信 |
| ユーザーへの送信 または グループへの送信 | 通知対象ユーザー/グループ |
| メディアのみによる送信 | Google Chat |

**メッセージ本文（UPDATE）:**

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

---

## 5. ユーザーメディアの設定

### 5.1 ユーザーへのメディア割り当て

Zabbix管理画面 > ユーザー > ユーザーを選択 > 「メディア」タブ

「追加」をクリックして以下を設定:

| 項目 | 設定値 |
|---|---|
| タイプ | Google Chat |
| 送信先 | Webhook URL（config.yamlで管理する場合は空文字でも可） |
| 有効な時間帯 | 1-7,00:00-24:00 |
| 重要度 | 通知したい重要度にチェック |

**送信先の設定方針:**

- `config.yaml` または環境変数でWebhook URLを管理する場合 → 空文字でも動作する
- ユーザーごとに異なるWebhook URLを使用する場合 → 各ユーザーの送信先にURLを設定する

---

## 6. グローバルマクロの設定

Zabbix管理画面 > 管理 > 一般 > マクロ

| マクロ名 | 値 | 説明 |
|---|---|---|
| `{$ZABBIX.URL}` | `https://zabbix.example.com` | ZabbixサーバーのURL（カードのリンクボタンに使用） |

---

## 7. 動作確認

### 7.1 Zabbixサーバーからの手動テスト

```bash
# zabbixユーザーで実行
sudo -u zabbix python3 /usr/lib/zabbix/alertscripts/zabbix_notify.py \
  "" \
  "テスト通知" \
  "ALERT_TYPE=PROBLEM
HOST_NAME=test-server
TRIGGER_NAME=テストアラート
TRIGGER_SEVERITY=Warning
EVENT_ID=99999
EVENT_DATE=2026.03.20
EVENT_TIME=12:00:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=test"

echo "終了コード: $?"
```

成功すると終了コード0が返り、Google Chatにカードが届く。

### 7.2 Zabbix管理画面からのテスト

メディアタイプ一覧ページから対象メディアタイプの「テスト」をクリックする。

| 項目 | 入力値 |
|---|---|
| 送信先 | Webhook URL |
| 件名 | テスト |
| メッセージ | `ALERT_TYPE=PROBLEM` 等の本文 |

### 7.3 アクションログの確認

通知が届かない場合はアクションログを確認する。

Zabbix管理画面 > 通知 > アクションログ

エラーメッセージと終了コードを確認し、[USAGE.md のトラブルシューティング](USAGE.md#7-トラブルシューティング)を参照する。
