# TASKS

## 完了済み

- [x] 初期実装（2026-03-11）
  - models.py, exceptions.py, parser.py, config.py, card_builder.py, webhook_sender.py, scripts/zabbix_notify.py
- [x] ユニットテスト実装（63件）
- [x] Gitリポジトリ初期化・pre-commit設定（2026-03-20）
- [x] バグ修正: webhook_sender.py の ConnectionError キャッチ漏れ（2026-03-20）
  - `requests.exceptions.ConnectionError` のみキャッチしていたため `builtins.ConnectionError` が漏れる問題を修正
- [x] Lint修正（ruff, mypy 全通過）（2026-03-20）

## 未着手

- [x] dev ブランチ作成（main から分岐）（2026-03-20）
- [ ] GitHub リモートリポジトリ作成・初回プッシュ
- [ ] GitHub Actions CI 動作確認
- [ ] 複数 Python バージョン（3.10/3.11/3.12/3.13）でのテスト実行確認
- [ ] docs/ 仕様書のアップデート確認
