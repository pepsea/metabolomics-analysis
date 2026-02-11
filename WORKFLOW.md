# Literature Radar Workflow

## システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                   Literature Radar System                    │
└─────────────────────────────────────────────────────────────┘

┌────────────────┐
│  run_config.json│  ← 設定ファイル（時間窓、ドメイン、閾値など）
└────────┬───────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Paper Fetching (fetch_papers.py)                   │
│                                                               │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ EuropePMC   │  │  PubMed  │  │ bioRxiv  │  │  arXiv  │ │
│  └──────┬──────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│         │              │              │              │       │
│         └──────────────┴──────────────┴──────────────┘       │
│                         │                                     │
│                         ▼                                     │
│              ┌──────────────────────┐                        │
│              │   Deduplication      │                        │
│              │   - By DOI/PMID      │                        │
│              │   - By Title         │                        │
│              └──────────┬───────────┘                        │
│                         │                                     │
└─────────────────────────┼─────────────────────────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │ fetched_papers.json │  ← 中間ファイル
                └─────────┬───────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Paper Processing (process_papers.py)               │
│                                                               │
│  For each domain:                                            │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  1. Relevance Screening                                │ │
│  │     - Remove off-topic papers                          │ │
│  │     - Filter reviews (if configured)                   │ │
│  │     - Tag paper type & study stage                     │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │  2. Claude API Scoring                                 │ │
│  │     - Novelty (0-20)                                   │ │
│  │     - Breakthrough (0-20)                              │ │
│  │     - Future Impact (0-20)                             │ │
│  │     - Rigor (0-15)                                     │ │
│  │     - Translational (0-15)                             │ │
│  │     - Community Signal (0-10)                          │ │
│  │     + Extract evidence anchors from abstracts          │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │  3. Selection with Constraints                         │ │
│  │     - Apply diversity rules                            │ │
│  │     - Apply time window priority                       │ │
│  │     - Select top N (min 3, max 10)                     │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │  4. Japanese Summarization                             │ │
│  │     - One-liner problem statement                      │ │
│  │     - What's new (bullets)                             │ │
│  │     - Key results (bullets)                            │ │
│  │     - Why it matters (translational)                   │ │
│  │     - Limitations & risks                              │ │
│  │     - Next actions (business-specific)                 │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ literature_radar_output.json │  ← 最終出力
         └──────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│  Output Structure                                            │
│                                                               │
│  {                                                            │
│    "run_date_utc": "2026-02-11",                            │
│    "domains": [                                              │
│      {                                                        │
│        "domain": "Metabolomics",                             │
│        "selected": [                                         │
│          {                                                    │
│            "rank": 1,                                        │
│            "scores": {...},                                  │
│            "evidence_anchors": [...],                        │
│            "summary_ja": {...}                               │
│          }                                                    │
│        ],                                                     │
│        "honorable_mentions": [...]                           │
│      },                                                       │
│      ...                                                      │
│    ]                                                          │
│  }                                                            │
└─────────────────────────────────────────────────────────────┘
```

## データフロー詳細

### Phase 1: Collection

```
Time Windows Strategy:
─────────────────────
last_2_days   │████│
last_7_days   │████████████████████│
last_30_days  │████████████████████████████████████████████████████████│

Priority: 2d → 7d → 30d
- まず2日間で strong papers (score ≥ 70) が min 必要数あるかチェック
- 不足なら7日間に拡大
- さらに不足なら30日間に拡大
```

### Phase 2: Scoring

```
Total Score (0-100):
─────────────────────
Novelty           ████████████████████ 20
Breakthrough      ████████████████████ 20
Future Impact     ████████████████████ 20
Rigor             ███████████████ 15
Translational     ███████████████ 15
Community Signal  ██████████ 10
                  ──────────────────────────
                                      100

Strong paper threshold: ≥ 70
```

### Phase 3: Diversity Constraints

```
Constraint Matrix:
──────────────────
Same author group:     Max 2 papers
Same subtopic:         Max 3 papers
Paper type balance:    Method ≥ 3, Application ≥ 3 (if possible)

Example Domain Selection (10 papers):
─────────────────────────────────────
Methods:       │■■■■■│ 5 papers
Applications:  │■■■■│ 4 papers
Theory:        │■│ 1 paper
```

## 実行モード比較

| モード | 期間 | 論文数/域 | 実行時間 | コスト | 用途 |
|--------|------|-----------|----------|--------|------|
| **Quick** | 2日 | 5 | ~5分 | ~$0.5 | 毎日チェック |
| **Default** | 2/7/30日 | 10 | ~10分 | ~$1-2 | 週次レポート |
| **Comprehensive** | 2/7/30/90日 | 15 | ~20分 | ~$3-5 | 月次深堀り |

## エラーハンドリング

```
┌──────────────────┐
│ API Rate Limit   │
│ Detected         │
└────────┬─────────┘
         │
         ▼
    Automatic retry
    with backoff
         │
         ▼
┌──────────────────┐
│ Continue or      │
│ partial results  │
└──────────────────┘


┌──────────────────┐
│ Missing abstract │
└────────┬─────────┘
         │
         ▼
    Mark as "missing"
    Lower confidence
         │
         ▼
┌──────────────────┐
│ Include in stats │
│ but flag clearly │
└──────────────────┘
```

## 品質保証メカニズム

### 1. Evidence-Based Scoring
```
Every score must be supported by:
- 1-3 evidence anchors
- Verbatim quotes from abstract
- ≤ 25 words per anchor
```

### 2. Anti-Hallucination
```
✓ Only use retrieved abstracts
✓ Mark missing data explicitly
✓ Flag speculative statements
✗ No invented numbers
✗ No assumptions beyond abstract
```

### 3. Diversity Enforcement
```
Pre-selection:  100 candidates
    ↓
Relevance filter: 80 candidates
    ↓
Score ranking: Top 30
    ↓
Diversity constraints applied
    ↓
Final selection: 10 papers
```

## パフォーマンス最適化

### Parallel Processing
```
Domain 1 (Metabolomics)  │═══════════════════│
Domain 2 (Lipidomics)    │═══════════════════│
Domain 3 (Proteomics)    │═══════════════════│
...                       Sequential (one domain at a time)

Within domain:
API calls  │═══│ Batched per domain
Parsing    │═══│ Vectorized operations
```

### Caching Strategy
```
├─ Query Results (1 hour TTL)
├─ Abstract Fetches (24 hour TTL)
└─ Deduplication Index (session)
```

## 拡張性

### カスタムドメイン追加
```python
# run_config.json に追加
{
  "query_dictionary": {
    "Custom Domain": "(keyword1 OR keyword2) AND (biology OR omics)"
  }
}
```

### カスタムスコアリング
```python
# process_papers.py の _build_scoring_prompt を編集
# 例: Business Impact基準を追加
```

### 出力形式の拡張
```python
# JSON → CSV, Excel, Notion, Slack などに変換
# 例: json_to_excel.py, json_to_slack.py などを追加
```

## セキュリティ

```
✓ API keys stored in environment variables
✓ No credentials in code
✓ .gitignore protects sensitive files
✓ Rate limiting respects API terms
✓ No data retention beyond session (optional)
```

## メンテナンス

### 日次
- [ ] 実行ログ確認
- [ ] エラー率モニタリング

### 週次
- [ ] 選定論文の手動レビュー
- [ ] スコアリング精度チェック

### 月次
- [ ] クエリ最適化
- [ ] 新規データソース検討
- [ ] コスト最適化レビュー
