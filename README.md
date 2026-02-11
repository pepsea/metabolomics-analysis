# Literature Radar Orchestrator

オミクス・バイオインフォマティクス・AI/エージェント・疾患メカニズム分野の最新論文を自動収集・評価・要約するシステム

## 概要

このシステムは、創薬・トランスレーショナル研究における意思決定を支援するため、8つのドメインから最新論文を収集し、重要度に基づいて自動選定・要約します。

### 対象ドメイン
1. **Metabolomics** (メタボロミクス)
2. **Lipidomics** (リピドミクス)
3. **Proteomics** (プロテオミクス)
4. **Transcriptomics** (トランスクリプトミクス)
5. **Genomics** (ゲノミクス)
6. **Bioinformatics** (バイオインフォマティクス)
7. **AI/Agents** (AI/エージェント)
8. **Disease Mechanism** (疾患メカニズム)

### 主要機能
- 複数の論文データベースから自動収集（EuropePMC, PubMed, bioRxiv, medRxiv, arXiv）
- AI（Claude）による論文評価・選定
- 日本語での構造化要約生成
- 機械可読なJSON形式での出力

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Anthropic API キーの設定

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

または、`.env`ファイルを作成：

```bash
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
source .env
```

### 3. 設定ファイルの準備

`run_config.json`を作成（初回実行時に自動生成されます）：

```json
{
  "run_date_utc": "2026-02-11",
  "time_windows": [
    {"name": "last_2_days", "days": 2},
    {"name": "last_7_days", "days": 7},
    {"name": "last_30_days", "days": 30}
  ],
  "max_selected_per_domain": 10,
  "min_selected_per_domain": 3,
  "source_priority": ["EuropePMC", "PubMed", "bioRxiv", "medRxiv", "arXiv"],
  "strict_sources_only": true,
  "require_peer_reviewed": false,
  "include_review_articles": false,
  "novelty_lookback_days": 90,
  "output_detail_level": "standard"
}
```

## 使用方法

### ステップ1: 論文の収集

```bash
python fetch_papers.py
```

これにより、各データソースから論文を収集し、`fetched_papers.json`に保存します。

**出力例:**
```
Literature Radar - Paper Fetcher
============================================================
Run date: 2026-02-11
Output file: fetched_papers.json
============================================================

============================================================
Domain: Metabolomics
============================================================

Time window: last_2_days (2 days)
Date range: 2026-02-09 to 2026-02-11
  [EuropePMC] Searching...
    Found 15 papers
  [PubMed] Searching...
    Found 12 papers
  [bioRxiv] Searching...
    Found 3 papers
Total for last_2_days: 30 papers

...

Total unique papers for Metabolomics: 45
```

### ステップ2: 論文の評価・選定

```bash
python process_papers.py
```

これにより、収集した論文をClaudeが評価・選定し、`literature_radar_output.json`に構造化された結果を保存します。

**出力例:**
```
Literature Radar - Paper Processor
============================================================
Loaded data from: fetched_papers.json
Run date: 2026-02-11
Domains: ['Metabolomics', 'Lipidomics', ...]
============================================================

============================================================
Processing domain: Metabolomics
Input papers: 45
============================================================
Calling Claude API for scoring and selection...
Selected: 8 papers
Honorable mentions: 5

...

Processing Summary:
  Metabolomics: 8/45 papers selected
  Lipidomics: 7/38 papers selected
  ...
```

### ワンステップ実行（推奨）

```bash
python fetch_papers.py && python process_papers.py
```

## 出力ファイル

### `fetched_papers.json`
論文収集の生データ（中間ファイル）

### `literature_radar_output.json`
最終的な評価・要約結果（メインアウトプット）

**構造:**
```json
{
  "run_date_utc": "2026-02-11",
  "time_windows": [...],
  "domains": [
    {
      "domain": "Metabolomics",
      "window_policy_used": "2d_only",
      "stats": {
        "retrieved": 45,
        "deduped": 45,
        "screened_in": 40,
        "selected": 8,
        "strong_threshold": 70
      },
      "selected": [
        {
          "rank": 1,
          "title": "論文タイトル",
          "date": "2026-02-10",
          "venue": "Nature Metabolism",
          "identifiers": {
            "doi": "10.1038/...",
            "pmid": "12345678"
          },
          "scores": {
            "novelty": 18,
            "breakthrough": 17,
            "future_impact": 19,
            "rigor": 14,
            "translational": 13,
            "community_signal": 9,
            "total": 90
          },
          "evidence_anchors": [
            "achieved 95% accuracy in metabolite annotation",
            "first demonstration of single-cell fluxomics"
          ],
          "summary_ja": {
            "one_liner": "単一細胞レベルでの代謝フラックス測定を実現",
            "whats_new": [
              "従来の細胞集団レベルから単一細胞レベルへの技術革新",
              "リアルタイム測定による動的代謝プロファイリング"
            ],
            "key_results": [
              "95%の精度で代謝物アノテーション",
              "1000細胞/時間のスループット達成"
            ],
            "why_it_matters": "腫瘍内不均一性の理解と個別化医療への応用が期待",
            "method_data": "LC-MS/MSベースのシングルセル代謝フラックス解析",
            "limitations_risks": [
              "現状では特定の代謝経路に限定",
              "サンプル前処理の標準化が必要"
            ],
            "next_actions": [
              "自社プラットフォームへの技術導入可能性を評価",
              "著者グループとの連携を検討",
              "ベンチマーク試験の実施"
            ]
          }
        }
      ],
      "honorable_mentions": [...]
    }
  ],
  "global_notes_ja": [...]
}
```

## 評価基準

各論文は以下の6つの基準で0-100点満点で評価されます：

| 基準 | 配点 | 評価内容 |
|------|------|----------|
| **Novelty** | 0-20 | 新規性（新しいタスク・手法・データ・モダリティ） |
| **Breakthrough** | 0-20 | ブレークスルー性（桁違いの改善または新機能） |
| **Future Impact** | 0-20 | 将来的影響（プラットフォーム性・拡張性） |
| **Rigor** | 0-15 | 厳密性（検証・ベンチマーク・サンプルサイズ） |
| **Translational** | 0-15 | トランスレーショナル関連性（標的・バイオマーカー） |
| **Community Signal** | 0-10 | コミュニティシグナル（ジャーナル・著者グループ） |

**Strong paper threshold**: Total score ≥ 70

## 選定制約

論文の多様性を確保するため、以下の制約があります：

- 同一著者グループ：最大2本
- 同一サブトピック：最大3本
- 可能な限り method論文 ≥ 3本、application論文 ≥ 3本

## Time Window戦略

1. **last_2_days**でstrong papers（score ≥ 70）が最低3本あれば、そこから選定
2. 不足なら**last_7_days**に拡大
3. さらに不足なら**last_30_days**に拡大

使用したポリシーは`window_policy_used`に記録されます。

## カスタマイズ

### クエリのカスタマイズ

`run_config.json`に`query_dictionary`を追加：

```json
{
  "query_dictionary": {
    "Metabolomics": "(metabolomics OR metabolome) AND (single-cell OR spatial)",
    "Lipidomics": "..."
  }
}
```

### ドメインの制限

特定のドメインのみ処理する場合：

```json
{
  "domains": ["Metabolomics", "Proteomics"]
}
```

### API使用量の最適化

論文数が多い場合、処理コストを削減するには：

```json
{
  "time_windows": [
    {"name": "last_2_days", "days": 2}
  ],
  "max_selected_per_domain": 5
}
```

## トラブルシューティング

### API Key エラー
```
Error: ANTHROPIC_API_KEY environment variable not set
```
→ 環境変数を設定してください

### 論文が取得できない
- ネットワーク接続を確認
- API rate limitに達していないか確認（各API間に0.5秒の待機時間あり）
- クエリが適切か確認

### JSON parse エラー
- Claudeのレスポンスが不正な場合があります
- `process_papers.py`を再実行してください

## API Rate Limits

各データソースには以下のrate limitがあります：

- **PubMed/NCBI**: 3 requests/second (スクリプトは0.34秒待機)
- **Europe PMC**: 制限緩やか
- **bioRxiv/medRxiv**: 制限緩やか
- **arXiv**: 制限緩やか

スクリプトは自動的に各リクエスト間に0.5秒待機します。

## コスト見積もり

### Claude API使用量（目安）

- 1ドメインあたり：約10,000-20,000 tokens（入力）+ 5,000-10,000 tokens（出力）
- 8ドメイン合計：約120,000-240,000 tokens
- コスト：約$1-3 per run（Sonnet 4.5使用時）

## ライセンス

MIT License

## 開発者向け情報

### ディレクトリ構造
```
article_search/
├── README.md
├── requirements.txt
├── run_config.json          # 設定ファイル
├── fetch_papers.py          # 論文収集スクリプト
├── process_papers.py        # 論文処理スクリプト
├── fetched_papers.json      # 中間出力（収集データ）
└── literature_radar_output.json  # 最終出力（評価結果）
```

### 拡張方法

1. **新しいデータソースの追加**
   - `fetch_papers.py`の`PaperFetcher`クラスに新しいfetchメソッドを追加

2. **評価基準の変更**
   - `process_papers.py`の`_build_scoring_prompt`メソッドを編集

3. **出力形式の変更**
   - JSONスキーマを維持しつつ、フィールドを追加可能

## サポート

問題や質問がある場合は、Issueを作成してください。
