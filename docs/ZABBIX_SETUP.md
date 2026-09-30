# Zabbix設定ガイド

## 1. 前提条件

- Zabbix 6.0以上
- Zabbixサーバーに Python 3.9以上がインストールされていること
- Google Chat Webhook URLを取得済みであること（取得方法は [USAGE.md](USAGE.md) を参照）。
  Chat API で送信する場合は代わりに [8章](#8-chat-api-で送信する復旧時に障害メッセージを更新) の準備を行う

---

## 2. スクリプトの配置

### 2.0 自動インストール（推奨）

`install.sh` を使うと以下を自動的に実行する:

```bash
# リポジトリを取得
git clone https://github.com/ttrip-ngs/zabbix-googlechat.git
cd zabbix-googlechat

# インストール（root 権限が必要）
sudo bash scripts/install.sh
```

手動でインストールする場合は以下の手順に従う。

### 2.1 alertscriptsディレクトリの確認

Zabbixの外部スクリプトディレクトリを確認する。デフォルトは `/usr/lib/zabbix/alertscripts`。

```bash
grep AlertScriptsPath /etc/zabbix/zabbix_server.conf
# 例: AlertScriptsPath=/usr/lib/zabbix/alertscripts
```

### 2.2 パッケージのインストール

```bash
pip install zabbix-googlechat
```

仮想環境を使用する場合:

```bash
python3 -m venv /opt/zabbix-googlechat/venv
/opt/zabbix-googlechat/venv/bin/pip install zabbix-googlechat
```

仮想環境を使用する場合、スクリプト1行目のshebangを仮想環境のPythonに変更する:

```python
#!/opt/zabbix-googlechat/venv/bin/python3
```

### 2.3 スクリプトのコピー

```bash
cp scripts/zabbix_notify.py /usr/lib/zabbix/alertscripts/
chmod +x /usr/lib/zabbix/alertscripts/zabbix_notify.py
```

### 2.4 設定ファイルの配置

```bash
sudo mkdir -p /etc/zabbix-googlechat
sudo cp config/config.yaml.example /etc/zabbix-googlechat/config.yaml

# Webhook URLを設定
sudo vi /etc/zabbix-googlechat/config.yaml
```

設定ファイルの探索順序（優先度順）:

1. 環境変数 `ZABBIX_GOOGLECHAT_CONFIG` で明示指定
2. `/etc/zabbix-googlechat/config.yaml`（FHS標準パス）
3. カレントディレクトリの `config/config.yaml`
4. 設定ファイルなし（環境変数 `GCHAT_WEBHOOK_URL` のみで動作）

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
TRIGGER_ID={TRIGGER.ID}
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
TRIGGER_ID={TRIGGER.ID}
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
TRIGGER_ID={TRIGGER.ID}
EVENT_DATE={EVENT.DATE}
EVENT_TIME={EVENT.TIME}
ACK_AUTHOR={USER.FULLNAME}
ACK_MESSAGE={ACK.MESSAGE}
ZABBIX_URL={$ZABBIX.URL}
ITEM_LASTVALUE={ITEM.LASTVALUE}
```

### 4.5 メッセージスタイルの指定（任意）

メッセージ本文に `CARD_STYLE` 行を追加すると、そのアクションだけ別スタイルで通知できる。
値は `detailed` / `medium` / `compact` / `text` のいずれか。省略時は設定ファイル
（`config.yaml` の `card_style` / 環境変数 `GCHAT_CARD_STYLE`、既定 `detailed`）の値が使われる。

例: 復旧通知だけコンパクト表示にする場合、RECOVERYのメッセージ本文に以下を追加する。

```
CARD_STYLE=compact
```

同一Zabbixサーバー内でも、重大アラートは `detailed`、復旧通知は `compact` のように
アクション単位で使い分けられる。不正な値を指定した場合は警告ログを出力し `detailed` に
フォールバックするため、通知自体は失われない。

---

## 5. ユーザーメディアの設定

### 5.1 ユーザーへのメディア割り当て

Zabbix管理画面 > ユーザー > ユーザーを選択 > 「メディア」タブ

「追加」をクリックして以下を設定:

| 項目 | 設定値 |
|---|---|
| タイプ | Google Chat |
| 送信先 | Webhook URL または Chat API のスペース名（config.yamlで管理する場合は空文字でも可） |
| 有効な時間帯 | 1-7,00:00-24:00 |
| 重要度 | 通知したい重要度にチェック |

送信先に `https://` で始まる Webhook URL を入れると、環境変数・config.yaml の送信先より優先される。
`spaces/` で始まるスペース名を入れると Chat API で送信する（[8章](#8-chat-api-で送信する復旧時に障害メッセージを更新)）。
ユーザー(宛先)ごとに Chat スペースを分けたい場合はこの方法を使う。
Zabbix HA で複数ノードに配備している場合も、ノードごとの config.yaml の違いに左右されない。
どちらでもない値(ラベル文字列など)を入れた場合は無視され、警告ログを出して環境変数・config.yaml の送信先を使う。

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
| 送信先 | Webhook URL またはスペース名（`spaces/XXXXXXXX`） |
| 件名 | テスト |
| メッセージ | `ALERT_TYPE=PROBLEM` 等の本文 |

### 7.3 アクションログの確認

通知が届かない場合はアクションログを確認する。

Zabbix管理画面 > 通知 > アクションログ

エラーメッセージと終了コードを確認し、[USAGE.md のトラブルシューティング](USAGE.md#7-トラブルシューティング)を参照する。

---

## 8. Chat API で送信する（復旧時に障害メッセージを更新）

Webhook では投稿済みのメッセージを更新できないため、障害と復旧が別々のメッセージになる。
Chat API（Chat アプリ + サービスアカウント）で送信すると、復旧時に障害発生のメッセージを
復旧内容で置き換える（Slack の「メッセージ更新」と同様の表示）。

### 8.1 動作

| アラート種別 | 動作 |
|---|---|
| PROBLEM | メッセージID `client-<接頭辞>-<EVENT.ID>` を付けて新規投稿する |
| RECOVERY | 同じメッセージIDのメッセージを復旧カードに置き換える。対象が無ければ（Webhook 時代の障害など）新規投稿する。更新が 400 / 403 / 404 で失敗した場合も新規投稿する |
| UPDATE | 新しいメッセージとして投稿する |

- 復旧時の `{EVENT.ID}` は障害イベントのIDになるため、アクションのメッセージ本文は変更不要
  （`EVENT_ID={EVENT.ID}` が PROBLEM / RECOVERY 両方の本文に含まれていること）
- メッセージIDはイベントIDから決まるので、投稿済みメッセージの記録を持たない
  （Zabbix HA のどちらのノードが送っても同じメッセージを更新できる）
- エスカレーションで同じ障害を再通知した場合は、同じIDが使用済みのため新しいメッセージとして投稿する。
  復旧時に更新されるのは最初のメッセージ
- 同じスペースに複数の Zabbix（別DB）から送る場合は、`message_id_prefix` を Zabbix ごとに変える。
  同じ接頭辞だと、Zabbix B の復旧が同じイベントIDを持つ Zabbix A の障害メッセージを上書きする

**注意: 復旧は通知されない。** メッセージの更新では Google Chat のプッシュ通知・未読は発生しない。
Webhook 送信では復旧時にも通知が届いていたため、復旧を通知で知る運用をしている場合は移行前に確認する。

**既知の制限**

- ID 付きの投稿が Google 側で成功したのに応答がタイムアウトした場合、リトライが ID 重複になり、
  障害メッセージが2件になる（通知は失われない。復旧時に更新されるのは1件目）
- 障害の送信がリトライ中に復旧が先に届いた場合、復旧カードが先に作られ、後から障害カードが
  ID なしで投稿されて残る

### 8.2 前提条件

- Google Workspace（Business / Enterprise）アカウント（Chat アプリの作成に必要）
- Google Cloud プロジェクト

### 8.3 Google Cloud 側の準備

1. Google Cloud コンソールで対象プロジェクトの「Google Chat API」を有効にする
2. 「IAM と管理 > サービスアカウント」でサービスアカウントを作成する（ロールの付与は不要）
3. 作成したサービスアカウントの「鍵 > 鍵を追加 > 新しい鍵を作成 > JSON」で鍵をダウンロードする
4. 「Google Chat API > 構成」で Chat アプリを設定する
   - アプリ名・アバターURL・説明を入力する
   - 機能で「スペースとグループの会話に参加する」を有効にする（無効だとスペースに追加できない）
   - 公開設定で、アプリをスペースに追加するユーザー（またはグループ）を指定する
5. 通知先のスペースを開き、「アプリと統合」から作成した Chat アプリを追加する
6. スペースのURL `https://mail.google.com/chat/u/0/#chat/space/XXXXXXXX` の `XXXXXXXX` を控える。
   スペース名は `spaces/XXXXXXXX`

### 8.4 Zabbix サーバー側の設定

鍵ファイルは秘密情報のため、zabbix ユーザーだけが読めるように配置する。
Zabbix HA の場合は全ノードに同じ鍵ファイル・同じ設定（`message_id_prefix` を含む）を配置する。

```bash
sudo install -o zabbix -g zabbix -m 600 service-account.json /etc/zabbix-googlechat/service-account.json
```

`/etc/zabbix-googlechat/config.yaml`:

```yaml
googlechat:
  # 既定の送信先スペース（ユーザーメディアの送信先で上書き可能）
  space: "spaces/XXXXXXXX"
  credentials_file: /etc/zabbix-googlechat/service-account.json
  # 同じスペースに複数の Zabbix から送る場合は Zabbix ごとに変える
  message_id_prefix: zbx
```

宛先ごとにスペースを分ける場合は、ユーザーメディアの送信先に `spaces/XXXXXXXX` を設定する。
送信先に Webhook URL を設定したユーザーは、`space` を設定していても従来どおり Webhook で送信する
（ユーザーごとに段階的に移行できる）。

送信先に `spaces/` を設定した宛先は、鍵が未設定・スペース名の形式が不正だと、ラベル文字列のように
config.yaml の送信先へフォールバックせず、設定エラー（終了コード1）で通知されない。
アクションログにエラーが出るので、移行時は各宛先でテスト送信する。

### 8.5 動作確認

7.1 の手動テストで、第1引数にスペース名を渡して PROBLEM を送り、同じ `EVENT_ID` で
`ALERT_TYPE=RECOVERY`（`RECOVERY_DATE` / `RECOVERY_TIME` 付き）を送る。
PROBLEM のメッセージが復旧カードに置き換われば成功。本番のメディアで `space` を使う前に必ず確認する
（ログに「更新が HTTP ... のため、新しいメッセージとして投稿します」が出る場合は更新できていない）。
同じ PROBLEM を2回送り、2回目が新しいメッセージとして投稿されることも確認する（エスカレーション時の挙動）。

| 症状 | 原因 |
|---|---|
| 設定エラー（サービスアカウント鍵を読み込めません） | 鍵ファイルのパス・権限・内容を確認する |
| 送信エラー (HTTP 401) | 鍵が無効（削除済み・別プロジェクト）。鍵を作り直す |
| 送信エラー (HTTP 403 / 404) | Chat アプリがスペースに追加されていない、またはスペース名の誤り |
