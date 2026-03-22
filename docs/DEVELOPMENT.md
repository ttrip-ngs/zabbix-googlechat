# 開発ガイド

## 1. 開発環境のセットアップ

### 1.1 リポジトリのクローン

```bash
git clone https://github.com/ttrip-ngs/zabbix-googlechat.git
cd zabbix-googlechat
git checkout dev
```

### 1.2 Python環境の準備

Python 3.9以上が必要。pyenvを使用した場合の例:

```bash
pyenv install 3.13.2
pyenv local 3.13.2
```

### 1.3 依存ライブラリのインストール

```bash
pip install -e ".[dev]"
```

### 1.4 pre-commitのセットアップ

```bash
pre-commit install
```

コミット時に以下のチェックが自動実行される:

- gitleaks（シークレット検出）
- trailing-whitespace（行末空白）
- end-of-file-fixer（ファイル末尾改行）
- check-yaml / check-toml / check-json（フォーマット検証）
- debug-statements（デバッグ文検出）
- ruff（Lint・フォーマット）

---

## 2. プロジェクト構成

```
zabbix-googlechat/
├── src/
│   └── zabbix_googlechat/        ← ライブラリ本体
│       ├── __init__.py
│       ├── models.py             ← データモデル（AlertType, Severity, ZabbixEvent）
│       ├── exceptions.py         ← カスタム例外クラス
│       ├── parser.py             ← Zabbixパラメータパーサー
│       ├── config.py             ← 設定管理
│       ├── card_builder.py       ← Google Chat Card v2ビルダー
│       └── webhook_sender.py     ← Webhook送信クライアント
├── scripts/
│   └── zabbix_notify.py          ← Zabbix外部スクリプト（エントリポイント）
├── tests/
│   ├── unit/                     ← ユニットテスト
│   │   ├── test_models.py
│   │   ├── test_parser.py
│   │   ├── test_config.py
│   │   ├── test_card_builder.py
│   │   └── test_webhook_sender.py
│   └── fixtures/
│       └── sample_zabbix_params.json
├── config/
│   └── config.yaml.example       ← 設定ファイルのサンプル
├── docs/                         ← ドキュメント
├── memo/history/                 ← 開発履歴
├── .github/workflows/ci.yml      ← GitHub Actions CI設定
├── .pre-commit-config.yaml       ← pre-commit設定
├── pyproject.toml                ← プロジェクト設定・依存関係
└── TASKS.md                      ← タスク管理
```

---

## 3. テスト

### 3.1 ユニットテストの実行

```bash
# 全テスト実行
python -m pytest tests/unit/ -v

# カバレッジ付き実行
python -m pytest tests/unit/ --cov=zabbix_googlechat --cov-report=term-missing

# 特定テストファイルのみ実行
python -m pytest tests/unit/test_webhook_sender.py -v

# 特定テストケースのみ実行
python -m pytest tests/unit/test_webhook_sender.py::TestGoogleChatWebhookSender::test_send_success -v
```

### 3.2 テスト構成

各テストファイルと対応するモジュール:

| テストファイル | 対象モジュール | テスト件数 |
|---|---|---|
| test_models.py | models.py | 13件 |
| test_parser.py | parser.py | 14件 |
| test_config.py | config.py | 14件 |
| test_card_builder.py | card_builder.py | 13件 |
| test_webhook_sender.py | webhook_sender.py | 8件 |

### 3.3 テストを追加する際の指針

- テストクラスは `Test{ClassName}` の命名規則に従う
- テストメソッドは `test_{機能}_{期待結果}` の形式で命名する
- `pytest.fixture` を使用して共通のセットアップを共有する
- HTTPテストには `responses` ライブラリを使用してWebhookをモックする

---

## 4. 品質チェック

### 4.1 Lint・フォーマット

```bash
# Lintチェック
python -m ruff check .

# 自動修正
python -m ruff check --fix .

# フォーマットチェック
python -m ruff format --check .

# フォーマット適用
python -m ruff format .
```

### 4.2 型チェック

```bash
python -m mypy src
```

### 4.3 セキュリティチェック

```bash
# コードの静的セキュリティ解析
python -m bandit -r src -ll

# 依存ライブラリの脆弱性チェック
python -m safety check
```

### 4.4 プッシュ・PR前の必須チェック

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest tests/unit/
```

---

## 5. Git運用

### 5.1 ブランチ構成

| ブランチ | 用途 |
|---|---|
| `main` | 本番リリース用安定版（直接プッシュ禁止） |
| `dev` | 開発のベースブランチ（PRのマージ先） |
| `feature/*` | 機能開発用（`dev` から分岐） |

### 5.2 開発フロー

```bash
# 1. devを最新化
git checkout dev
git pull origin dev

# 2. featureブランチ作成
git checkout -b feature/機能名-20260320

# 3. 実装・テスト

# 4. プッシュ前チェック
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest tests/unit/

# 5. コミット（pre-commitが自動実行される）
git add <変更ファイル>
git commit -m "機能の説明を日本語で記述"

# 6. プッシュ
git push origin feature/機能名-20260320

# 7. GitHub で dev への PR を作成
```

### 5.3 コミットメッセージの規則

- 日本語で記述する
- 変更内容が具体的にわかるように記述する

```
# 良い例
ユーザー認証機能を追加
バグ修正: ConnectionError のキャッチ漏れを修正
テスト: webhook_sender のテストカバレッジを向上

# 悪い例
fix bug
update
WIP
```

---

## 6. CI/CD

### 6.1 GitHub Actions

`.github/workflows/ci.yml` で以下が自動実行される:

- Python 3.9 / 3.10 / 3.11 / 3.12 / 3.13 でのテスト実行
- ruff Lint・フォーマットチェック
- mypy 型チェック
- bandit セキュリティチェック

PR作成後はActions結果を確認し、全チェックが通ることを確認してからレビューを依頼する。

---

## 7. ドキュメントの管理

ドキュメントは `docs/` 配下に配置する。

| ファイル | 内容 |
|---|---|
| docs/SPEC.md | システム設計仕様書 |
| docs/USAGE.md | 利用ガイド |
| docs/CONFIGURATION.md | 設定リファレンス |
| docs/ZABBIX_SETUP.md | Zabbix設定ガイド |
| docs/DEVELOPMENT.md | 開発ガイド（本ファイル） |

コードの変更に伴い仕様が変わった場合は、対応するドキュメントも同一コミットで更新する。

### 7.1 開発履歴

主要な変更は `memo/history/` 配下に記録する。

```
memo/history/
├── 001_initial_implementation.md
├── 002_git_init_and_fixes.md
└── ...
```

ファイル名は連番 + 変更内容の概要。後の開発に必要な情報（設計判断の理由、既知の課題等）を中心に記録する。
