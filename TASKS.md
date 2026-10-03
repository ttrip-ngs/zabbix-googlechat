# TASKS

## 完了済み

- [x] 初期実装（2026-03-11）
  - models.py, exceptions.py, parser.py, config.py, card_builder.py, webhook_sender.py, scripts/zabbix_notify.py
- [x] ユニットテスト実装（63件）
- [x] Gitリポジトリ初期化・pre-commit設定（2026-03-20）
- [x] バグ修正: webhook_sender.py の ConnectionError キャッチ漏れ（2026-03-20）
  - `requests.exceptions.ConnectionError` のみキャッチしていたため `builtins.ConnectionError` が漏れる問題を修正
- [x] Lint修正（ruff, mypy 全通過）（2026-03-20）
- [x] dev ブランチ作成（main から分岐）（2026-03-20）
- [x] 導入方法の改善（2026-03-22）
  - `src/zabbix_googlechat/cli.py` 新規作成（パッケージ内CLIロジック、設定ファイル探索）
  - `pyproject.toml` に console_scripts 追加（`zabbix-googlechat-notify` コマンド）
  - `scripts/zabbix_notify.py` をシンプルなラッパーに書き換え
  - `scripts/install.sh` 新規作成（Zabbixサーバーへの自動インストール）
  - `tests/unit/test_cli.py` 新規作成（17件追加、計80件）
  - `docs/QUICKSTART.md` 新規作成（運用者向け導入手順）
  - README.md、docs/USAGE.md、docs/ZABBIX_SETUP.md、docs/SPEC.md 更新
- [x] メッセージスタイル複数化（2026-05-14）
  - `CardStyle` enum（detailed / medium / compact / text）を追加
  - `card_builder.py` に `MediumCardBuilder` / `CompactCardBuilder` / `PlainTextBuilder` と `build_payload` ファクトリを追加
  - `config.yaml` の `card_style` / 環境変数 `GCHAT_CARD_STYLE` / メッセージ本文 `CARD_STYLE` で選択可能
  - 不正値は警告ログを出して `detailed` にフォールバック（通知は失わない）
  - ユニットテスト24件追加（計104件）、ドキュメント・設定サンプル更新

- [x] GitHub リモートリポジトリ作成・初回プッシュ（ttrip-ngs/zabbix-googlechat、PR #1〜で運用中）
- [x] メッセージスタイル機能のリリース（2026-06-10）
  - プッシュ・PR前ローカル品質チェック全通過（ruff check / ruff format --check / mypy src / pytest 105件）
  - PR #8（feature/googlechat-message-styles-20260514 → dev）作成・CI成功・マージ、feature ブランチ削除
  - PR #9（dev → main）作成・CI成功・マージ（origin/main = 612b30c）
- [x] GitHub Actions CI 動作確認（PR #8 / #9 で全ジョブ success）
- [x] 複数 Python バージョン（3.9/3.10/3.11/3.12/3.13）でのテスト実行確認（CIマトリクスで全通過）
- [x] Webhook URL の優先順位変更（2026-09-23）
  - `{ALERT.SENDTO}` が `https://` で始まる場合は環境変数・config.yaml より優先する
  - 目的: Zabbix のユーザーメディアごとに Chat スペースを振り分ける。HA の各ノードで config.yaml の値が違っても宛先が変わらない
  - ラベル文字列・空文字は従来どおり無視して環境変数 → config.yaml を使う
  - ユニットテスト3件追加・2件変更（計109件）、ドキュメント更新、バージョン 1.1.0
- [x] Chat API 送信で復旧時に障害メッセージを更新（2026-09-30）
  - `space` 設定（または `{ALERT.SENDTO}` に `spaces/XXXX`）で Chat アプリ + サービスアカウントで送信
  - PROBLEM にメッセージID `client-<接頭辞>-<EVENT.ID>` を付け、RECOVERY で同じIDを更新（状態保存なし）
  - ユニットテスト35件追加（計144件）、ドキュメント更新、バージョン 1.2.0
  - 実スペース（GCP_API_TEST）で確認（2026-10-03）: PROBLEM 投稿、再通知は 409 → IDなし投稿、
    RECOVERY で同じメッセージが置き換わる、障害メッセージなしの RECOVERY は新規投稿、UPDATE は新規投稿
- [x] headline スタイル追加（2026-10-03）
  - 見出し `【障害】ホスト`、トリガー名を状態色の太字、状態色の塗りつぶしボタン。絵文字なし
  - 復旧はヘッダーなしの1段に畳んでグレー表示（チャットを開いたとき障害中のものに集中できる）
  - ユニットテスト11件追加（計155件）

## 未着手

（なし）
