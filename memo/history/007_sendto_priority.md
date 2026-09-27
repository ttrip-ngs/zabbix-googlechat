# 007: Webhook URL の優先順位を {ALERT.SENDTO} 優先に変更（2026-09-23）

## 背景

mdo5 の Zabbix で障害通知の宛先を分ける(ネットワーク管理者用 / 現場ごと / 検証用の Chat スペース)。
宛先ごとの Webhook URL は Zabbix のユーザーメディアの「送信先」に持たせ、`{ALERT.SENDTO}` で渡す。

従来の優先順位は「環境変数 > config.yaml > {ALERT.SENDTO}」だった。このため config.yaml に
`webhook_url` があるノードでは、宛先ごとの URL が無視されて全通知が1つのスペースに集まる。
実際に HA の2ノードで config.yaml が食い違っていた(藤崎は空、小郡は URL あり)ため、
小郡がアクティブになると振り分けが壊れる状態だった。

## 変更内容

- `NotificationConfig.load()`: `alert_sendto` が `https://` で始まる場合、最後に `webhook_url` を上書きする
- 空文字・ラベル文字列(例: `gchat-matsuura-gaku`)は無視し、環境変数 → config.yaml の順で使う
- `validate()` のエラーメッセージ、docs(README / CONFIGURATION / USAGE / SPEC)の優先順位の記述を更新
- テスト: `test_load_priority_yaml_over_sendto` を `test_load_priority_sendto_over_yaml` に変更、
  `test_load_priority_sendto_over_env` / `test_load_non_url_sendto_falls_back_to_yaml` を追加

## 既存の運用への影響

- メディアタイプのスクリプト引数1番目に URL を直書きしている構成では、その URL が使われる
  (藤崎では従来どおり。小郡では従来 config.yaml の URL が勝っていたが、引数の URL に揃う)
- 引数1番目が `{ALERT.SENDTO}` で、メディアの送信先がラベル文字列の構成は従来どおり config.yaml の URL を使う

## 移行時の注意

- 新版は HA の両ノードに同じタイミングで配備する(片方だけ新版だと、アクティブノードによって振り分けが変わる)
- 引数1番目を `{ALERT.SENDTO}` にしたメディアタイプへ移す前に、対象ユーザー全員の送信先を URL にする。
  ラベルのまま残すと、config.yaml が空のノードでは設定エラーで通知が落ちる
- 送信先が URL でない場合は警告ログを出す(値はログに出さない)
- バージョンを 1.1.0 に上げた(両ノードの配備版を `pip show` で確認できるように)

## 品質確認

- ローカル: ruff check / ruff format --check / mypy src / pytest 109件 すべて通過（Python 3.9.25）
- CLI 経由で送信先の決定を確認(送信は差し替え): SENDTO=URL → SENDTO / ラベル → config.yaml / 空 → config.yaml
