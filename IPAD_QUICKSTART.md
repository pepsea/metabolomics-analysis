# 📱 iPadで使う - クイックスタート

最も簡単な方法で、iPadから Literature Radar を使えるようにします。

---

## 🎯 最速セットアップ（10分）

### ステップ1️⃣: GitHubにコードをアップロード

**Macで実行:**

```bash
cd /Users/yoshinorisatomi/Documents/claude/article_search

# Gitリポジトリ初期化（まだの場合）
git init

# 全ファイルを追加
git add .
git commit -m "Initial commit: Literature Radar for iPad"

# GitHubリポジトリを作成（ブラウザで）
# https://github.com/new で新しいリポジトリを作成
# 名前: literature-radar
# Public or Private: お好みで

# リモートリポジトリを追加してプッシュ
git remote add origin https://github.com/YOUR_USERNAME/literature-radar.git
git branch -M main
git push -u origin main
```

**⚠️ 重要**: `YOUR_USERNAME` を自分のGitHubユーザー名に置き換えてください

---

### ステップ2️⃣: API Keyを登録

1. **GitHubリポジトリページ**を開く
   - https://github.com/YOUR_USERNAME/literature-radar

2. **Settings** タブ → **Secrets and variables** → **Actions**

3. **New repository secret** をクリック

4. 以下を入力:
   - **Name**: `ANTHROPIC_API_KEY`
   - **Secret**: あなたのAnthropicAPIキー（`sk-ant-...`）

5. **Add secret** をクリック

---

### ステップ3️⃣: iPadから実行！

**iPadのSafariまたはChromeで:**

1. **リポジトリページを開く**
   - https://github.com/YOUR_USERNAME/literature-radar

2. **Actions** タブをタップ

3. 左側の **Literature Radar** をタップ

4. 右上の **Run workflow** ボタンをタップ

5. **プリセットを選択** (初回は `default` でOK)

6. **Run workflow** をタップ

7. **完了を待つ**（約10分）
   - 緑色のチェックマークが表示されたら完了

8. **結果を確認**
   - ワークフロー名をタップ
   - 下部の **Artifacts** セクションからダウンロード
   - または、リポジトリの `outputs/` フォルダを確認

---

## 📥 結果のダウンロード方法

### 方法A: Artifacts からダウンロード

1. 完了したワークフロー実行ページを開く
2. ページ下部の **Artifacts** セクション
3. `literature-radar-YYYYMMDD_HHMMSS` をタップ
4. ZIPファイルがダウンロードされる
5. 解凍してMarkdownファイルを開く

### 方法B: リポジトリから直接閲覧

1. リポジトリのトップページに戻る
2. `outputs/` フォルダを開く
3. 最新の `literature_radar_*.md` ファイルをタップ
4. **GitHubが自動でMarkdownをレンダリング**して表示！

---

## ⏰ 毎日自動実行の設定

**すでに設定済み！** 何もしなくても毎朝9時（JST）に自動実行されます。

変更したい場合は、`.github/workflows/literature_radar.yml` を編集:

```yaml
schedule:
  - cron: '0 0 * * *'  # 毎日 0:00 UTC = 9:00 JST
```

他の時間帯に変更する例:
- `'0 12 * * *'` → 毎日 21:00 JST
- `'0 0 * * 1'` → 毎週月曜日 9:00 JST

---

## 🎨 プリセット一覧

iPadから実行するときに選べるプリセット:

| プリセット | 説明 | 実行時間 |
|-----------|------|----------|
| `default` | 標準設定（2/7/30日、10本/域） | 約10分 |
| `quick` | クイック（2日、5本/域） | 約5分 |
| `comprehensive` | 詳細（90日、15本/域） | 約20分 |
| `weekly` | 週次レポート | 約10分 |
| `monthly` | 月次レポート | 約15分 |
| `metabolomics_only` | 代謝系のみ | 約3分 |
| `ai_focus` | AI関連のみ | 約3分 |

---

## 📱 おすすめiPadアプリ

生成されたMarkdownファイルを快適に閲覧:

1. **GitHub Mobile** (無料)
   - 公式アプリ
   - Markdownの表示が綺麗
   - プッシュ通知対応

2. **Working Copy** (Pro版推奨)
   - Gitクライアント
   - オフラインでも閲覧可能
   - Markdown編集も可能

3. **iA Writer** (有料)
   - Markdownエディタ
   - 美しいレンダリング

4. **Safari/Chrome** (無料)
   - GitHubのWeb UIで十分

---

## 🔔 通知を受け取る

### GitHub通知設定

1. GitHubアプリをインストール
2. **Settings** → **Notifications**
3. **Actions** の通知をONに
4. 実行完了時にiPadに通知が届く

### Slack通知（オプション）

`.github/workflows/literature_radar.yml` に追加:

```yaml
- name: Notify Slack
  env:
    SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
  run: |
    curl -X POST $SLACK_WEBHOOK \
      -H 'Content-Type: application/json' \
      -d '{"text":"📚 Literature Radar completed!"}'
```

Slack Webhook URLをGitHub Secretsに登録:
- Secret name: `SLACK_WEBHOOK`
- Secret value: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`

---

## ✅ チェックリスト

初回セットアップ:
- [ ] GitHubリポジトリを作成
- [ ] コードをpush
- [ ] `ANTHROPIC_API_KEY` をSecretsに登録
- [ ] iPadからテスト実行
- [ ] 結果を確認

---

## 🆘 困ったときは

### エラー: "Resource not accessible by integration"

**原因**: GitHub Actionsの権限不足

**解決**:
1. リポジトリの **Settings** → **Actions** → **General**
2. **Workflow permissions** を **Read and write permissions** に変更
3. **Save** をクリック

### エラー: "ANTHROPIC_API_KEY not found"

**原因**: API Keyが登録されていない

**解決**:
1. Settings → Secrets → Actions
2. `ANTHROPIC_API_KEY` が正しく登録されているか確認
3. キーの値にスペースや改行が入っていないか確認

### 実行が途中で止まる

**原因**: タイムアウトまたはAPI制限

**解決**:
1. `quick` プリセットを試す（処理時間短縮）
2. Anthropic APIの残高を確認
3. GitHub Actionsのログを確認してエラー内容を特定

---

## 💡 使い方のコツ

### 平日朝のルーティンに組み込む

1. 毎朝9時に自動実行
2. 朝食中にiPadで結果をチェック
3. 重要な論文があればチームに共有

### 週次レビュー会議で活用

1. 毎週月曜に `weekly` プリセットで実行
2. 会議前にMarkdownをチームに配布
3. Next Actionsをタスク管理ツールに追加

### カスタムプリセットを作成

`generate_config.py` に新しいプリセットを追加:

```python
"my_custom": {
    **base_config,
    "domains": ["Metabolomics", "AI/Agents"],
    "max_selected_per_domain": 5,
}
```

---

## 🎉 完了！

これでiPadから Literature Radar を使えるようになりました。

**最初の実行:**
1. iPadでGitHubを開く
2. Actions → Run workflow
3. 10分待つ
4. 結果を確認

**2回目以降:**
- 自動実行されるので確認するだけ！

---

**何か困ったことがあれば `IPAD_SETUP.md` の詳細版を参照してください。**
