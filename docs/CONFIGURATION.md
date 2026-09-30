# 設定リファレンス

## 1. 設定方法の優先順位

設定は以下の優先順位で適用される。高い優先度の設定が低い優先度の設定を上書きする。

```
優先度1 (最高): 環境変数
優先度2:        config/config.yaml
```

例: 環境変数 `GCHAT_WEBHOOK_URL` が設定されていれば、`config.yaml` の `webhook_url` は無視される。

**送信先だけは `{ALERT.SENDTO}` 引数が最優先になる**(`https://` で始まる Webhook URL、
または `spaces/` で始まる Chat API のスペース名の場合)。
Zabbix のユーザーメディアごとに送信先の Chat スペースを振り分けるため。
`{ALERT.SENDTO}` が空やラベル文字列のときは、環境変数 → `config.yaml` の順で使う。

**送信方式**: スペース名(`space`)が決まれば Chat API、そうでなければ Webhook で送信する。
`{ALERT.SENDTO}` が Webhook URL の場合は、`space` を設定していても Webhook で送信する。
複数ノード(Zabbix HA)に配備する場合、各ノードの `config.yaml` の値が違っても、
メディアに URL を設定した宛先は同じスペースに届く。

---

## 2. 環境変数

`.env` ファイルに記述するか、システム環境変数として設定する。

### 2.1 必須設定

Webhook と Chat API のどちらかを設定する（`{ALERT.SENDTO}` で指定する場合は不要）。

| 変数名 | 説明 | 例 |
|---|---|---|
| `GCHAT_WEBHOOK_URL` | Google Chat Webhook URL（Webhook で送信する場合） | `https://chat.googleapis.com/v1/spaces/XXX/messages?key=YYY&token=ZZZ` |
| `GCHAT_SPACE` | 送信先スペース名（Chat API で送信する場合） | `spaces/XXXXXXXX` |
| `GCHAT_CREDENTIALS_FILE` | サービスアカウント鍵(JSON)のパス（Chat API で送信する場合は必須） | `/etc/zabbix-googlechat/service-account.json` |

### 2.2 任意設定

| 変数名 | 説明 | デフォルト | 例 |
|---|---|---|---|
| `ZABBIX_URL` | ZabbixサーバーのベースURL | "" | `https://zabbix.example.com` |
| `GCHAT_TIMEOUT` | HTTPリクエストタイムアウト（秒） | 10 | `30` |
| `GCHAT_MAX_RETRIES` | 送信失敗時の最大リトライ回数 | 3 | `5` |
| `GCHAT_CARD_STYLE` | メッセージスタイル（detailed / medium / compact / text） | detailed | `compact` |
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

  # メッセージスタイル: detailed / medium / compact / text
  # 環境変数 GCHAT_CARD_STYLE で上書き可能
  card_style: detailed

  # Chat API の送信先スペース名（設定すると Webhook ではなく Chat API で送信する）
  # 環境変数 GCHAT_SPACE で上書き可能
  # space: "spaces/XXXXXXXX"

  # サービスアカウント鍵（JSON）のパス（Chat API で送信する場合は必須）
  # 環境変数 GCHAT_CREDENTIALS_FILE で上書き可能
  # credentials_file: /etc/zabbix-googlechat/service-account.json

  # メッセージIDの接頭辞（Chat API で送信する場合）
  # message_id_prefix: zbx

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

#### googlechat.card_style

Google Chat に送信するメッセージの表示スタイル。

| 値 | 構造 | 用途 |
|---|---|---|
| `detailed` | 2セクション・各項目を topLabel + text の2行で表示（既定） | 情報量重視 |
| `medium` | 2セクション構造は維持・各項目を `絵文字 ラベル: 値` の1行に圧縮 | 構造を残しつつ省スペース |
| `compact` | ヘッダー + 本文(textParagraph)1枚 + ボタンに集約 | カード1枚に集約 |
| `text` | カード(cardsV2)を使わないプレーンテキスト | 最小スペース |

- デフォルト: `detailed`（既存インストールは設定変更不要で従来表示のまま）
- 環境変数 `GCHAT_CARD_STYLE` で上書き可能
- Zabbixアクションのメッセージ本文に `CARD_STYLE=xxx` を記載するとアクション単位で上書きできる
  （未記載なら設定ファイル / 環境変数の値を使用）
- 不正な値を指定した場合は警告ログを出力してフォールバックする（通知は失われない）。
  メッセージ本文の `CARD_STYLE` が不正なら設定ファイル / 環境変数の値へ、設定ファイル /
  環境変数の値が不正なら `detailed` へフォールバックする
- 優先順位は次の通り:

```
優先度1 (最高): メッセージ本文の CARD_STYLE
優先度2:        環境変数 GCHAT_CARD_STYLE
優先度3 (最低): config.yaml の googlechat.card_style
```

#### googlechat.space

Chat API で送信する場合の送信先スペース名（`spaces/XXXXXXXX`）。

- 設定すると Webhook ではなく Chat API で送信し、復旧時に障害発生のメッセージを復旧内容で置き換える
- Chat アプリをスペースに追加しておく必要がある（手順は [ZABBIX_SETUP.md 8章](ZABBIX_SETUP.md#8-chat-api-で送信する復旧時に障害メッセージを更新)）
- `{ALERT.SENDTO}` に `spaces/XXXXXXXX` を設定するとユーザーメディア単位で上書きできる

#### googlechat.credentials_file

Chat アプリとして認証するサービスアカウント鍵（JSON）のパス。

- `space` を設定した場合は必須
- 秘密情報のため、zabbix ユーザーだけが読める権限（600）で配置する

#### googlechat.message_id_prefix

Chat API で投稿するメッセージのID `client-<接頭辞>-<EVENT.ID>` の接頭辞。

- デフォルト: `zbx`
- config.yaml でのみ設定できる（環境変数は無い）
- 英小文字・数字・ハイフンの20文字以内
- 同じスペースに複数の Zabbix（別DB）から送る場合は、イベントIDの重複で別の障害のメッセージを
  更新しないよう Zabbix ごとに変える（例: `zbx-fujisaki` / `zbx-ogori`）。
  同じDBを使う Zabbix HA の各ノードは同じ値にする

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
| `CARD_STYLE` | 固定値 | メッセージスタイルのアクション単位上書き（detailed / medium / compact / text）。省略可 |

### 4.5 アクション単位でスタイルを切り替える

メッセージ本文に `CARD_STYLE` を追加すると、そのアクションだけ別スタイルで通知できる。
同一Zabbixサーバー内で、重大アラートは `detailed`、復旧通知は `compact` といった使い分けが可能。

```
ALERT_TYPE=RECOVERY
HOST_NAME={HOST.NAME}
TRIGGER_NAME={TRIGGER.NAME}
TRIGGER_SEVERITY={TRIGGER.SEVERITY}
EVENT_ID={EVENT.ID}
EVENT_DATE={EVENT.DATE}
EVENT_TIME={EVENT.TIME}
RECOVERY_DATE={EVENT.RECOVERY.DATE}
RECOVERY_TIME={EVENT.RECOVERY.TIME}
ZABBIX_URL={$ZABBIX.URL}
CARD_STYLE=compact
```
