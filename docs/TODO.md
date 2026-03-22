# TODO

## 完了済み

- [x] プロジェクト基盤構築（pyproject.toml, .gitignore, .pre-commit-config.yaml）
- [x] モデル層（models.py, exceptions.py）
- [x] パーサー層（parser.py）
- [x] 設定層（config.py）
- [x] カードビルダー層（card_builder.py）
- [x] Webhook送信層（webhook_sender.py）
- [x] エントリポイント（scripts/zabbix_notify.py）
- [x] ユニットテスト 63件実装
- [x] CI設定（.github/workflows/ci.yml）
- [x] Gitリポジトリ初期化・pre-commit設定
- [x] バグ修正: ConnectionError キャッチ漏れ
- [x] ドキュメント整備（SPEC.md, USAGE.md, CONFIGURATION.md, ZABBIX_SETUP.md, DEVELOPMENT.md）

## バックログ

- [ ] GitHub リモートリポジトリ作成・初回プッシュ
- [ ] 複数 Python バージョン（3.9/3.10/3.11/3.12/3.13）でのテスト実行確認
- [ ] 統合テストの追加（実際のWebhookを使用したE2Eテスト）
- [ ] Zabbix 7.x対応確認
- [ ] ログローテーション設定例の追加
