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

## 未着手

（なし）
