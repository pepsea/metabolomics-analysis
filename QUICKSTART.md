# Quick Start Guide

## 5分で始める Literature Radar

### 1. セットアップ（初回のみ）

```bash
# ディレクトリに移動
cd /Users/yoshinorisatomi/Documents/claude/article_search

# 依存パッケージをインストール
pip install -r requirements.txt

# API キーを設定
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 2. 実行

**最も簡単な方法：**
```bash
./run_literature_radar.sh
```

これだけです！スクリプトが自動的に：
1. 論文を収集
2. Claude で評価
3. 結果を `literature_radar_output.json` に保存

### 3. 結果の確認

```bash
# 結果ファイルを開く
open literature_radar_output.json

# または、サマリーを表示
cat literature_radar_output.json | python3 -m json.tool | head -50
```

---

## カスタマイズ版

### プリセットを使う

```bash
# クイックスキャン（2日間のみ、速い）
python3 generate_config.py quick
./run_literature_radar.sh

# 包括的スキャン（90日間、詳細）
python3 generate_config.py comprehensive
./run_literature_radar.sh

# 週次レポート
python3 generate_config.py weekly
./run_literature_radar.sh
```

### 利用可能なプリセット

| プリセット | 説明 | 期間 | 論文数/ドメイン |
|-----------|------|------|----------------|
| `default` | 標準設定 | 2/7/30日 | 最大10本 |
| `quick` | クイックスキャン | 2日 | 最大5本 |
| `comprehensive` | 包括的スキャン | 2/7/30/90日 | 最大15本 |
| `peer_reviewed_only` | 査読済みのみ | 2/7/30日 | 最大10本 |
| `preprints_focus` | プレプリント優先 | 2/7/30日 | 最大10本 |
| `metabolomics_only` | 代謝系のみ | 2/7/30日 | 最大10本 |
| `ai_focus` | AI関連のみ | 2/7/30日 | 最大10本 |
| `weekly` | 週次レポート | 7日 | 最大10本 |
| `monthly` | 月次レポート | 30日 | 最大20本 |

---

## 手動実行（ステップバイステップ）

### ステップ1: 設定ファイルを生成

```bash
python3 generate_config.py
```

対話的にプリセットを選択できます。

### ステップ2: 論文を収集

```bash
python3 fetch_papers.py
```

結果は `fetched_papers.json` に保存されます。

### ステップ3: 論文を評価

```bash
python3 process_papers.py
```

結果は `literature_radar_output.json` に保存されます。

---

## 定期実行の設定

### Cron（Linux/Mac）

毎日午前9時に実行：

```bash
crontab -e
```

以下を追加：

```
0 9 * * * cd /Users/yoshinorisatomi/Documents/claude/article_search && /bin/bash run_literature_radar.sh >> radar_log.txt 2>&1
```

### Launchd（Mac推奨）

`~/Library/LaunchAgents/com.literatureradar.daily.plist` を作成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.literatureradar.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/yoshinorisatomi/Documents/claude/article_search/run_literature_radar.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/yoshinorisatomi/Documents/claude/article_search/radar_log.txt</string>
    <key>StandardErrorPath</key>
    <string>/Users/yoshinorisatomi/Documents/claude/article_search/radar_error.txt</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>your-api-key-here</string>
    </dict>
</dict>
</plist>
```

有効化：

```bash
launchctl load ~/Library/LaunchAgents/com.literatureradar.daily.plist
```

---

## トラブルシューティング

### Q: "ANTHROPIC_API_KEY not set" エラー

**A:** API キーを設定してください：

```bash
export ANTHROPIC_API_KEY='your-api-key'
```

永続化する場合は `~/.bashrc` または `~/.zshrc` に追加：

```bash
echo 'export ANTHROPIC_API_KEY="your-api-key"' >> ~/.zshrc
source ~/.zshrc
```

### Q: 論文が0件

**A:**
- ネットワーク接続を確認
- 日付範囲を広げる（`weekly` または `monthly` プリセット）
- クエリをカスタマイズ

### Q: 処理が遅い

**A:**
- `quick` プリセットを使用
- 特定のドメインのみに絞る（`metabolomics_only` など）

### Q: コストを抑えたい

**A:**
- `quick` プリセット使用
- `max_selected_per_domain` を減らす
- 実行頻度を減らす（週1回など）

---

## 次のステップ

✅ 基本的な実行ができたら：

1. **結果の可視化**: JSON を Excel/Notion/Slack に連携
2. **クエリのカスタマイズ**: 自社の関心領域に合わせて調整
3. **アラート設定**: 重要論文が見つかったら通知
4. **チーム共有**: 定期レポートとして配信

詳細は [README.md](README.md) を参照してください。
