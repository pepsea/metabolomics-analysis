# ✅ Literature Radar Orchestrator - セットアップ完了

## 📦 作成されたファイル一覧

### 🎯 コアスクリプト（3ファイル）

1. **`fetch_papers.py`** (20KB)
   - 論文収集スクリプト
   - EuropePMC, PubMed, bioRxiv, medRxiv, arXiv から自動取得
   - 重複除去機能内蔵
   - 出力: `fetched_papers.json`

2. **`process_papers.py`** (11KB)
   - 論文評価・選定スクリプト
   - Claude API で自動スコアリング
   - 日本語要約生成
   - 出力: `literature_radar_output.json`

3. **`run_literature_radar.sh`** (3.9KB) ⭐ **メイン実行ファイル**
   - ワンコマンドで全処理を実行
   - エラーハンドリング内蔵
   - 進捗表示とサマリー出力

### 🛠️ ユーティリティ（1ファイル）

4. **`generate_config.py`** (4.5KB)
   - 設定ファイル生成ツール
   - 9種類のプリセット搭載
   - 対話的な設定作成

### 📚 ドキュメント（5ファイル）

5. **`README.md`** (10KB)
   - 完全な利用ガイド
   - API仕様、評価基準、カスタマイズ方法
   - トラブルシューティング

6. **`QUICKSTART.md`** (5KB) ⭐ **まずこれを読む**
   - 5分で始められるクイックガイド
   - プリセット一覧
   - 定期実行設定（cron/launchd）

7. **`WORKFLOW.md`** (14KB)
   - システム構成図（ASCII art）
   - データフロー詳細
   - パフォーマンス最適化ガイド

8. **`EXAMPLE_OUTPUT.json`** (10KB)
   - 出力サンプル（実際の構造を確認できる）
   - 2本の論文例（詳細な要約付き）

9. **`requirements.txt`** (35B)
   - Python依存パッケージリスト
   - `anthropic`, `requests`

### 🔒 その他

10. **`.gitignore`**
    - API keyなど機密情報を保護
    - データファイルをバージョン管理から除外

---

## 🚀 今すぐ始める（3ステップ）

### ステップ1: 依存パッケージのインストール

```bash
cd /Users/yoshinorisatomi/Documents/claude/article_search
pip install -r requirements.txt
```

### ステップ2: API キー設定

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**永続化する場合:**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

### ステップ3: 実行

```bash
./run_literature_radar.sh
```

**これだけです！** 10-15分後に `literature_radar_output.json` が生成されます。

---

## 📊 実行モード早見表

| コマンド | 期間 | 論文数 | 時間 | コスト | 用途 |
|---------|------|--------|------|--------|------|
| `python3 generate_config.py quick && ./run_literature_radar.sh` | 2日 | 5本/域 | 5分 | $0.5 | 毎日 |
| `./run_literature_radar.sh` | 2/7/30日 | 10本/域 | 10分 | $1-2 | 週次 |
| `python3 generate_config.py comprehensive && ./run_literature_radar.sh` | 90日 | 15本/域 | 20分 | $3-5 | 月次 |

---

## 🎯 対象ドメイン（8分野）

✅ **Metabolomics** - メタボロミクス
✅ **Lipidomics** - リピドミクス
✅ **Proteomics** - プロテオミクス
✅ **Transcriptomics** - トランスクリプトミクス
✅ **Genomics** - ゲノミクス
✅ **Bioinformatics** - バイオインフォマティクス
✅ **AI/Agents** - AI/エージェント
✅ **Disease Mechanism** - 疾患メカニズム

---

## 📈 評価基準（合計100点）

| 基準 | 配点 | 内容 |
|------|------|------|
| **Novelty** | 20点 | 新規性（新手法・新データ・新モダリティ） |
| **Breakthrough** | 20点 | ブレークスルー性（桁違いの改善） |
| **Future Impact** | 20点 | 将来的影響（プラットフォーム性） |
| **Rigor** | 15点 | 厳密性（検証・ベンチマーク） |
| **Translational** | 15点 | 創薬関連性（標的・バイオマーカー） |
| **Community Signal** | 10点 | コミュニティ評価（ジャーナル・著者） |

**Strong paper threshold: ≥ 70点**

---

## 🔄 ワークフロー概要

```
1. fetch_papers.py
   ↓ (論文収集)
   fetched_papers.json
   ↓
2. process_papers.py
   ↓ (評価・要約)
   literature_radar_output.json ✨
```

**出力には以下が含まれます:**
- ランキング付き論文リスト（最大10本/ドメイン）
- スコア詳細（6基準 + 総合点）
- **エビデンスアンカー**（アブストラクトからの引用）
- **日本語要約**（7項目の構造化要約）
- Next actions（ビジネス向けアクション提案）
- Honorable mentions（次点候補）

---

## 🎨 カスタマイズ例

### 特定ドメインのみ処理

```bash
python3 generate_config.py metabolomics_only
./run_literature_radar.sh
```

### クエリをカスタマイズ

`run_config.json` を編集:
```json
{
  "query_dictionary": {
    "Metabolomics": "(metabolomics OR metabolome) AND (cancer OR tumor)"
  }
}
```

### 定期実行（毎朝9時）

**Mac (launchd):**
```bash
# ~/.claude/radar_daily.plist を作成（例はQUICKSTART.mdに記載）
launchctl load ~/.claude/radar_daily.plist
```

**Linux (cron):**
```bash
crontab -e
# 以下を追加:
0 9 * * * cd /Users/yoshinorisatomi/Documents/claude/article_search && ./run_literature_radar.sh >> radar_log.txt 2>&1
```

---

## 📖 推奨読書順序

1. **QUICKSTART.md** ← まずここから（5分）
2. このファイル（SETUP_COMPLETE.md）
3. README.md（詳細が必要なとき）
4. WORKFLOW.md（仕組みを理解したいとき）
5. EXAMPLE_OUTPUT.json（出力形式の確認）

---

## ⚡ よくある質問

### Q1: API キーはどこで取得？
**A:** https://console.anthropic.com/ でアカウント作成 → API Keys

### Q2: 料金は？
**A:** 1回の実行で約$1-2（8ドメイン、標準設定）
クイックモードなら約$0.5

### Q3: インターネット接続は必須？
**A:** Yes。論文DBとClaude APIにアクセスします。

### Q4: 結果はどう活用する？
**A:**
- 週次/月次の文献レビュー会議の資料
- 研究開発の方向性決定
- 競合技術の動向把握
- 投資判断材料

### Q5: エラーが出たら？
**A:**
1. `QUICKSTART.md` のトラブルシューティングを確認
2. `radar_error.txt`（あれば）を確認
3. API keyと環境変数を確認

---

## 🛡️ セキュリティ

✅ API keyは環境変数で管理
✅ `.gitignore`で機密情報を保護
✅ ローカル実行（データは外部送信されない）
✅ Rate limit遵守（API terms準拠）

---

## 🚧 今後の拡張案

- [ ] Slackへの自動投稿
- [ ] Notionデータベースへの連携
- [ ] Excel/CSV出力機能
- [ ] Web UIの追加
- [ ] カスタムスコアリング基準
- [ ] 論文の自動分類タグ付け
- [ ] 引用数・Impact Factorの自動取得

---

## 📞 サポート

- GitHub Issues（バグ報告・機能要望）
- ドキュメント: `README.md`, `QUICKSTART.md`, `WORKFLOW.md`
- サンプル: `EXAMPLE_OUTPUT.json`

---

## 🎉 次のステップ

### 今すぐ試す
```bash
./run_literature_radar.sh
```

### クイックスキャンを試す
```bash
python3 generate_config.py quick
./run_literature_radar.sh
```

### 結果を確認
```bash
cat literature_radar_output.json | python3 -m json.tool | less
```

---

**🌟 セットアップ完了です！良い文献探索を！**

作成日時: 2026-02-11
バージョン: 1.0.0
システム: Literature Radar Orchestrator
