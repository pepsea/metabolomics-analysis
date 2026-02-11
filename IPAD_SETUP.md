# 📱 iPadから使う方法

Literature Radar を iPad から使用するための3つの方法を紹介します。

---

## 🎯 方法の比較

| 方法 | 難易度 | 設定時間 | 費用 | おすすめ度 |
|------|--------|----------|------|------------|
| **1. GitHub Actions** | ⭐ 簡単 | 10分 | 無料 | ⭐⭐⭐⭐⭐ |
| **2. Streamlit Cloud** | ⭐⭐ 普通 | 15分 | 無料 | ⭐⭐⭐⭐ |
| **3. Working Copy + SSH** | ⭐⭐⭐ 難しい | 30分 | 一部有料 | ⭐⭐⭐ |

---

## 方法1: GitHub Actions（最推奨）⭐

iPadのブラウザから**ボタン1つで実行**。結果は自動でGitHubに保存。

### ✅ メリット
- 📱 iPadのブラウザだけで完結
- 🆓 完全無料（GitHub Actions は月2,000分まで無料）
- ⏰ スケジュール実行も可能（毎日自動実行）
- 📥 結果はGitHubで閲覧・ダウンロード可能

### 📋 セットアップ手順

#### 1. GitHubリポジトリを作成

```bash
# Macで実行（初回のみ）
cd /Users/yoshinorisatomi/Documents/claude/article_search

# Gitリポジトリ初期化
git init
git add .
git commit -m "Initial commit: Literature Radar"

# GitHubにpush（事前にGitHubでリポジトリ作成）
git remote add origin https://github.com/YOUR_USERNAME/literature-radar.git
git branch -M main
git push -u origin main
```

#### 2. API Keyをシークレットに登録

1. GitHubリポジトリページを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. Name: `ANTHROPIC_API_KEY`
5. Secret: あなたのAnthropicAPIキーを貼り付け
6. **Add secret** をクリック

#### 3. iPadから実行

1. **iPadのSafariで** `https://github.com/YOUR_USERNAME/literature-radar` を開く
2. **Actions** タブをクリック
3. 左サイドバーの **Literature Radar** をクリック
4. 右上の **Run workflow** ボタンをクリック
5. プリセットを選択（default/quick/comprehensiveなど）
6. **Run workflow** をクリック

#### 4. 結果を確認

- **進行状況**: Actions タブで実行ログをリアルタイム確認
- **完了後**:
  - `outputs/` ディレクトリに結果が自動保存（リポジトリのコミット履歴に残る）
  - **Artifacts** から直接ダウンロードも可能（90日間保持）

### 📅 毎日自動実行（オプション）

`.github/workflows/literature_radar.yml` の `schedule` セクションがすでに設定済み：

```yaml
schedule:
  - cron: '0 0 * * *'  # 毎日 JST 9:00に自動実行
```

何もしなくても毎朝自動で最新論文をチェックします！

---

## 方法2: Streamlit Cloud（Web UI）

ブラウザで使える**Webアプリ版**。UIで操作できます。

### ✅ メリット
- 🖥️ グラフィカルなUI
- 📱 iPadのブラウザで使える
- 🆓 無料（Streamlit Community Cloud）
- 📊 プレビュー機能付き

### 📋 セットアップ手順

#### 1. 必要なファイルを追加

`requirements.txt` に追記：

```bash
# 既存の内容
anthropic>=0.40.0
requests>=2.31.0

# 追加
streamlit>=1.30.0
```

#### 2. Streamlit Cloudにデプロイ

1. https://streamlit.io/cloud にアクセス
2. GitHubアカウントでサインイン
3. **New app** をクリック
4. リポジトリ、ブランチ、`streamlit_app.py` を選択
5. **Advanced settings** で環境変数を設定:
   - `ANTHROPIC_API_KEY`: あなたのAPIキー
6. **Deploy** をクリック

#### 3. iPadから使用

1. 発行されたURL（例: `https://YOUR_APP.streamlit.app`）をiPadのSafariで開く
2. プリセットを選択
3. **Run Literature Radar** ボタンをクリック
4. 完了後、MarkdownまたはJSONをダウンロード

### 🖼️ スクリーンショット（イメージ）

```
┌─────────────────────────────────────────┐
│ 📚 Literature Radar Orchestrator       │
├─────────────────────────────────────────┤
│ ⚙️ Configuration                        │
│   Preset: [default ▼]                  │
│   API Key: [••••••••••••]              │
│                                         │
│ ┌─────────────────────────────────────┐│
│ │  🚀 Run Literature Radar            ││
│ └─────────────────────────────────────┘│
│                                         │
│ 📊 Domains: 8 | Sources: 5             │
└─────────────────────────────────────────┘
```

---

## 方法3: Working Copy + SSH（上級者向け）

iOSアプリ **Working Copy** を使ってSSH接続し、リモートサーバーで実行。

### ✅ メリット
- 🔒 完全なコントロール
- 🖥️ 自分のサーバーで実行

### ❌ デメリット
- 💰 Working Copy Proが必要（有料）
- 🖥️ VPS/サーバーが必要
- ⚙️ 設定が複雑

### 📋 セットアップ手順

#### 1. VPS/サーバーを用意

- AWS EC2、DigitalOcean、さくらVPSなど
- Ubuntu 22.04推奨

#### 2. サーバーにコードをデプロイ

```bash
# サーバーにSSH接続
ssh user@your-server.com

# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/literature-radar.git
cd literature-radar

# 環境構築
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY='your-key'
```

#### 3. Working Copyアプリ（iPad）

1. App Storeから **Working Copy** をダウンロード（Pro版推奨）
2. リポジトリをクローン
3. SSH設定でサーバーに接続
4. iPadから直接スクリプトを実行

#### 4. 実行用ショートカット作成

iOSショートカットアプリで**SSH経由で実行するショートカット**を作成：

```
SSH接続 → cd literature-radar → ./run_literature_radar.sh
```

---

## 🎯 推奨する使い方（実践編）

### 🏆 ベストプラクティス

**平日の朝9時に自動実行 + iPadから確認**

1. **GitHub Actions** でスケジュール実行を有効化
2. 毎朝9時に自動で最新論文をチェック
3. GitHubからSlack/メールに通知（GitHub Actions + Webhook）
4. iPadで通知を受け取り、GitHubで結果を確認
5. 重要な論文があればチームに共有

### 📱 iPadでの閲覧体験

生成されたMarkdownファイルは以下のアプリで快適に閲覧：

- **Working Copy** (Git + Markdown viewer)
- **iA Writer** (Markdown editor)
- **Notion** (GitHubと連携してインポート)
- **GitHub Mobile** (公式アプリ)

---

## 🔧 カスタマイズ例

### 通知機能を追加

`.github/workflows/literature_radar.yml` に追加：

```yaml
- name: Send notification to Slack
  if: success()
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
  run: |
    LATEST_MD=$(ls -t outputs/literature_radar_*.md | head -1)
    SUMMARY=$(head -50 "$LATEST_MD")

    curl -X POST $SLACK_WEBHOOK_URL \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"📚 Literature Radar Report generated!\n\`\`\`$SUMMARY\`\`\`\"}"
```

### Notion連携

結果をNotionデータベースに自動保存：

```yaml
- name: Upload to Notion
  env:
    NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
    NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
  run: |
    python3 scripts/upload_to_notion.py
```

---

## 🆘 トラブルシューティング

### Q: GitHub Actionsが失敗する

**A:** 以下を確認：
1. `ANTHROPIC_API_KEY` がSecretsに正しく設定されているか
2. API keyの残高があるか
3. Actions タブのログでエラー内容を確認

### Q: Streamlit Cloudでタイムアウトする

**A:**
- `quick` プリセットを使用（処理時間を短縮）
- Streamlit Cloudの無料枠には実行時間制限あり
- 長時間処理はGitHub Actionsを推奨

### Q: iPadでMarkdownが見づらい

**A:**
- **Working Copy** アプリを使用（Markdown表示に最適化）
- または、GitHubのWeb UIで直接表示（自動レンダリング）

---

## 💰 コスト見積もり

### GitHub Actions（推奨）
- **月間実行回数**: 30回（1日1回）
- **1回あたりの時間**: 約10分
- **月間合計**: 300分
- **コスト**: **無料**（2,000分/月まで無料）

### Streamlit Cloud
- **コスト**: **無料**（Community Cloud）
- **制限**:
  - 3つまでの公開アプリ
  - 実行時間制限あり

### VPS（方法3）
- **コスト**: 月500円〜
- DigitalOcean: $6/month
- さくらVPS: 580円/month

---

## 📚 関連ファイル

- `.github/workflows/literature_radar.yml` - GitHub Actionsの設定
- `streamlit_app.py` - Streamlit Webアプリ
- `run_literature_radar.sh` - メイン実行スクリプト

---

## ✨ 次のステップ

1. ✅ GitHub Actionsをセットアップ
2. ✅ iPadから手動実行してテスト
3. ✅ 毎日自動実行を有効化
4. ✅ 通知機能を追加（Slack/メールなど）
5. ✅ Notionなどのツールと連携

---

**🎉 これでiPadからいつでも最新論文をチェックできます！**

Version: 1.1.0
Updated: 2026-02-11
