# 003: 導入方法の改善（pip install 対応）

日付: 2026-03-22

## 背景

開発者向け構造のため Zabbix サーバー運用者が導入するには以下の問題があった:
- `scripts/zabbix_notify.py` が `../src/` への `sys.path` 依存で単体動作不可
- `pip install` で CLI コマンドが生成されない（console_scripts 未設定）
- ドキュメントが開発者目線

## 実施内容

### 新規ファイル

**`src/zabbix_googlechat/cli.py`**
- `scripts/zabbix_notify.py` の `main()` / `setup_logging()` をパッケージ内に移動
- 設定ファイル探索を柔軟化（`_find_config_path()`）:
  1. 環境変数 `ZABBIX_GOOGLECHAT_CONFIG`
  2. `/etc/zabbix-googlechat/config.yaml`（FHS標準）
  3. `config/config.yaml`（カレントディレクトリ）
  4. None（環境変数のみで動作）

**`scripts/install.sh`**
- Python バージョン確認（3.10以上）
- pip install 実行
- `AlertScriptsPath` を `/etc/zabbix/zabbix_server.conf` から自動検出
- スクリプト配置・権限設定
- `/etc/zabbix-googlechat/config.yaml` 作成

**`tests/unit/test_cli.py`**
- `_find_config_path()` の各探索パステスト（6件）
- `setup_logging()` テスト（3件）
- `main()` 正常系・異常系テスト（8件）
- 合計 17件追加（既存63件 + 17件 = 80件）

**`docs/QUICKSTART.md`**
- 運用者向け導入クイックスタートガイド

### 変更ファイル

**`scripts/zabbix_notify.py`**
- `sys.path` 操作を削除
- `from zabbix_googlechat.cli import main` のシンプルなラッパーに変更

**`pyproject.toml`**
- `[project.scripts]` セクション追加
- `zabbix-googlechat-notify = "zabbix_googlechat.cli:main"` 登録

**`README.md`**
- 冒頭に運用者向けクイックスタートセクション追加
- `docs/QUICKSTART.md` をドキュメント一覧に追加

**`docs/USAGE.md`**
- インストール方法を pip install ベースに更新
- デプロイ手順に install.sh 自動インストールと手動インストールを整理
- 設定ファイル探索順序の説明を追加

**`docs/ZABBIX_SETUP.md`**
- install.sh による自動インストール案内を追加（セクション 2.0）
- 手動インストール手順を pip install ベースに更新

**`docs/SPEC.md`**
- アーキテクチャ図を cli.py 経由の構造に更新
- モジュール依存関係図を更新
- `3.6 cli.py` セクション追加（`_find_config_path()`、`setup_logging()`、`main()` の仕様）
- エントリポイント仕様（セクション4）を CLIコマンド + alertscripts ラッパーの2形式に更新

## テスト結果

- ユニットテスト: 80件全通過（Python 3.13.2）
- ruff lint: 全通過
- ruff format: 全通過
- mypy: 8ファイル全通過（0エラー）

## 重要事項

- `scripts/zabbix_notify.py` は `pip install zabbix-googlechat` 済み前提のラッパー
- 設定ファイル探索で環境変数指定が存在しない場合、他パスへのフォールバックなし（意図した設定パスを確実に使用させるため）
- `setup_logging()` は `force=True` で既存ハンドラを上書きし、設定ファイルのログレベルを反映
