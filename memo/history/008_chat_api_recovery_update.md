# 008: Chat API 送信で復旧時に障害メッセージを更新（2026-09-30）

## 背景

Webhook 送信では障害と復旧が別々のメッセージになる。Slack 連携のように、復旧時は障害発生の
メッセージを書き換えて表現したい。

## 調査結果（Google Chat の仕様）

- Incoming Webhook は新規投稿のみ。投稿済みメッセージの更新手段は無い
- `spaces.messages.patch` はアプリ認証の場合「呼び出した Chat アプリが作成したメッセージ」だけ更新できる。
  Webhook が投稿したメッセージは Chat アプリからも更新できない
- よって障害発生時の投稿から Chat API（Chat アプリ + サービスアカウント）に切り替える必要がある
- `spaces.messages.create` の `messageId` にクライアント指定ID（`client-` で始まり英小文字・数字・ハイフン、
  63文字以内、スペース内で一意）を付けられる
- `spaces.messages.patch` の `allowMissing=true` は、クライアント指定IDのメッセージが無ければ新規作成する

## 設計

- メッセージIDを `client-<接頭辞>-<EVENT.ID>` とし、PROBLEM で付与、RECOVERY で同じIDを PATCH する。
  復旧時の `{EVENT.ID}` は障害イベントのIDなので、アクション本文の変更は不要
- IDがイベントIDから決まるため、投稿済みメッセージ名の保存（状態ファイル・ロック・掃除）が不要。
  Zabbix HA のどちらのノードから送っても同じメッセージを更新できる
- RECOVERY は `allowMissing=true` で PATCH するため、障害メッセージが無い場合（Webhook 時代の障害、
  削除済み等）も通知は失われず新規投稿になる
- PROBLEM の ID が使用済み（エスカレーションの再通知）の場合は ID なしで新規投稿する。
  重複時のステータスは公式ドキュメントに記載が無く、Google API の慣例（ALREADY_EXISTS = 409）を想定しつつ、
  400 で返る場合も ID なしで投稿し直す（通知を失わないため）。409 は ERROR ログを出さない
- RECOVERY の PATCH が 400 / 403 / 404 の場合は ID なしで新規投稿する（updateMask の拒否、Chat アプリの作り直しで
  旧アプリのメッセージを更新できない場合などに復旧通知を失わないため）
- UPDATE（確認・コメント）は ID なしで新規投稿する
- 送信方式は `space` の有無で決める。`{ALERT.SENDTO}` が `spaces/` ならスペース名、`https://` なら
  Webhook URL として最優先（Webhook URL の場合は設定済みの space を使わない）。ユーザーメディア単位で
  段階的に移行できる
- 接頭辞 `message_id_prefix`（既定 `zbx`）は、同じスペースに別DBの Zabbix から送る場合の衝突回避用

## 変更内容

- `chat_api_sender.py` 新規: `GoogleChatApiSender`（create / upsert）、`build_message_id`
- `webhook_sender.py`: リトライ処理を基底クラス `_RetryingSender` に切り出し（Webhook の挙動は不変）
- `config.py`: `space` / `credentials_file` / `message_id_prefix`、環境変数 `GCHAT_SPACE` /
  `GCHAT_CREDENTIALS_FILE`、`{ALERT.SENDTO}` の `spaces/` 判定、送信方式別の検証
- `cli.py`: 送信方式の分岐。`success=False`（2xx 以外の想定外ステータス）を送信エラー(終了コード2)にする
  （従来は成功扱いで終了コード0を返していた）
- 依存に `google-auth` を追加。Python 3.9 では import 時に FutureWarning を出すため、
  Chat API 送信時だけ import する
- mypy: google-auth の一部関数に型注釈が無いため `untyped_calls_exclude` に google.auth / google.oauth2 を追加
- docs: ZABBIX_SETUP.md 8章（Google Cloud 側の準備・鍵の配置・動作確認）、CONFIGURATION / SPEC / README
- バージョン 1.2.0

## 未確認事項

- ID 重複時の実際のステータス（409 / 400）。同じ PROBLEM を2回送って確認する
- 実スペースでの送信・更新は未実施（Google Cloud プロジェクト・Chat アプリ・サービスアカウントが必要）。
  Google Cloud コンソールの Chat アプリ構成手順（インタラクティブ機能・公開設定）は構築時に確定させる
