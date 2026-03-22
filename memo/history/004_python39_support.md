# Python 3.9+ 対応

## 変更内容

Python 3.10以上を要求していた設定を 3.9以上に拡張した。

### ソースコード

対象3ファイル（cli.py, config.py, webhook_sender.py）は既に `from __future__ import annotations` が追加済みだったため、追加修正不要だった。

### pyproject.toml

- `requires-python`: `>=3.10` → `>=3.9`
- ruff `target-version`: `py310` → `py39`
- mypy `python_version`: `3.10` → `3.9`

### .github/workflows/ci.yml

- quality/securityジョブの `python-version`: `"3.10"` → `"3.9"`
- unit-testsマトリクス: `["3.10", ...]` → `["3.9", "3.10", ...]`
- カバレッジアップロード条件: `== '3.10'` → `== '3.9'`

### ドキュメント

- README.md, docs/DEVELOPMENT.md, docs/QUICKSTART.md, docs/USAGE.md, docs/ZABBIX_SETUP.md, docs/SPEC.md, docs/TODO.md のバージョン表記を更新

## 検証結果

- ruff check: 全チェック通過
- ruff format: 全ファイルフォーマット済み
- mypy: 8ファイル全通過
- pytest: 80件全件通過
