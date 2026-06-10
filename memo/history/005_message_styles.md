# メッセージスタイル複数化

## 背景

従来の Google Chat 通知は `cardsV2` で「問題情報」「イベント情報」の2セクション、各項目を
`decoratedText`（topLabel + text の2行）で描画していた。情報量は十分だが1通あたりの縦幅が大きく、
複数アラートが並ぶと一覧性が悪いという要望を受け、コンパクト表示を含む複数スタイルを選択可能にした。

## 変更内容

### models.py

- `CardStyle(str, Enum)` を追加（`DETAILED` / `MEDIUM` / `COMPACT` / `TEXT`）
- `DEFAULT_CARD_STYLE` 定数（`"detailed"`）を追加
- `ZabbixEvent` に `card_style: str = ""` フィールドを追加（アクション単位の上書き値、空=未指定）

### parser.py

- `_KEY_MAP` に `CARD_STYLE` → `card_style` を追加
- `parse_message_body` のフィールド設定ループに `card_style` を追加（値の検証はせず生文字列を格納）

### config.py

- `NotificationConfig` に `card_style` フィールド（既定 `detailed`）を追加
- `from_env` / `from_yaml` / `load` で読み込み。環境変数 `GCHAT_CARD_STYLE` で上書き可能
- `validate` で不正値を検出した場合は `ConfigurationError` を投げず、警告ログを出して
  `detailed` にフォールバック（スタイル指定ミスで通知自体が失われるのを防ぐ）

### card_builder.py

- 共通処理を基底クラス `_CardBuilderBase` に集約（ヘッダー構築・Zabbixリンク生成・
  アクションボタン・絵文字解決・cardsV2ラップ）
- `GoogleChatCardBuilder` は `detailed` 実装として維持（既存 import / テスト互換）
- `MediumCardBuilder`: 2セクション維持・各項目を topLabel 無しの1行 `decoratedText` に圧縮
- `CompactCardBuilder`: ヘッダー + `textParagraph` 1枚 + ボタン。改行は `<br>`、装飾は `<b>`
- `PlainTextBuilder`: `cardsV2` を使わない `{"text": ...}`。改行 `\n` と `*bold*` 記法
- `build_payload(event, style)` ファクトリ関数を追加。未知 style は警告のうえ `detailed` に
  フォールバック

### cli.py

- `GoogleChatCardBuilder` 直接呼び出しを `build_payload` に変更
- スタイル優先順位を解決。メッセージ本文 `CARD_STYLE` が `CardStyle` の有効値ならそれを採用し、
  不正値（タイプミス等）なら警告ログを出して設定ファイル（検証済み）の値へフォールバックする
- `text` スタイルは `cardsV2` キーを持たないため、ログ出力を style 表記に変更

### スタイル選択の優先順位

```
優先度1 (最高): メッセージ本文の CARD_STYLE キー
優先度2:        環境変数 GCHAT_CARD_STYLE
優先度3:        config.yaml の googlechat.card_style
優先度4 (最低): 既定値 detailed
```

### ドキュメント・設定

- `config/config.yaml.example`、`docs/CONFIGURATION.md`、`docs/USAGE.md`、`docs/SPEC.md`、
  `docs/ZABBIX_SETUP.md`、`README.md` を更新

## 検証結果

- pytest: 104件全件通過（スタイル関連テスト24件追加）
- ruff check / format: 全通過
- mypy: 8ファイル全通過
- 手動疎通: compact / text スタイルのペイロード構造を目視確認

## 今後の注意点

- `compact` の `textParagraph` は `\n` ではなく `<br>` で改行する必要がある（Google Chat 仕様）。
  装飾は `<b>` 等の限定 HTML サブセットのみ対応
- `text` スタイルは `cardsV2` を持たないため、ペイロードを参照する箇所では `cardsV2` の不在を
  考慮すること
