# 📝 変更履歴

## v1.1.0 (2026-02-11)

### ✨ 新機能
- **Markdownレポート出力対応**
  - JSON形式に加えて、読みやすいMarkdown形式でレポートを生成
  - 日付時刻をファイル名に含めたタイムスタンプ形式（例: `literature_radar_20260211_143000.md`）
  - 出力ファイルは `outputs/` ディレクトリに整理

### 🔧 変更点
- **出力形式の改善**
  - 従来: `literature_radar_output.json` (単一ファイル、上書き)
  - 新方式: `outputs/literature_radar_YYYYMMDD_HHMMSS.json` + `.md` (履歴保持)

- **ファイル構成**
  ```
  outputs/
  ├── literature_radar_20260211_120000.json
  ├── literature_radar_20260211_120000.md
  ├── literature_radar_20260211_143000.json
  └── literature_radar_20260211_143000.md
  ```

### 📄 Markdownレポートの特徴
- 📊 サマリーテーブル（ドメイン別統計）
- 📑 論文ごとの構造化セクション
  - メタデータ（日付、ジャーナル、DOI、PMID等）
  - スコア詳細（6項目 + 総合点）
  - 選定理由（日本語）
  - Evidence Anchors（引用）
  - 要約セクション（新規性、主要結果、重要性、制限事項、Next Actions）
- ✅ Next ActionsはMarkdownチェックボックス形式
- 🎖️ Honorable Mentions
- 📝 ドメイン別・全体の注記

### 📚 サンプルファイル
`outputs/SAMPLE_literature_radar_20260211_120000.md` を参照

---

## v1.0.0 (2026-02-11初期版)

### 初期リリース
- 8ドメイン対応（Metabolomics, Lipidomics, Proteomics, etc.）
- 5データソース対応（EuropePMC, PubMed, bioRxiv, medRxiv, arXiv）
- Claude API による自動評価・選定
- JSON形式での出力
