#!/usr/bin/env python3
"""
Literature Radar - Paper Processing Script
Scores, selects, and summarizes papers using Claude API
Outputs as Markdown file with timestamp
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import anthropic

# Configuration
INPUT_FILE = "fetched_papers.json"
OUTPUT_DIR = "outputs"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Score thresholds
STRONG_PAPER_THRESHOLD = 70
MAX_SELECTED = 10
MIN_SELECTED = 3


class PaperProcessor:
    def __init__(self, fetched_data: Dict, api_key: str):
        self.data = fetched_data
        self.config = fetched_data["config"]
        self.client = anthropic.Anthropic(api_key=api_key)
        self.output = {
            "run_date_utc": self.config["run_date_utc"],
            "time_windows": self.config["time_windows"],
            "domains": [],
            "global_notes_ja": []
        }

    def score_and_select_domain(self, domain: str, papers: List[Dict]) -> Dict:
        """Score and select papers for a single domain using Claude"""

        print(f"\n{'='*60}")
        print(f"Processing domain: {domain}")
        print(f"Input papers: {len(papers)}")
        print(f"{'='*60}")

        if not papers:
            return {
                "domain": domain,
                "window_policy_used": "no_papers",
                "stats": {
                    "retrieved": 0,
                    "deduped": 0,
                    "screened_in": 0,
                    "selected": 0,
                    "strong_threshold": STRONG_PAPER_THRESHOLD
                },
                "selected": [],
                "honorable_mentions": [],
                "notes_ja": ["取得された論文がありませんでした。"]
            }

        # Prepare prompt
        prompt = self._build_scoring_prompt(domain, papers)

        # Call Claude
        print("Calling Claude API for scoring and selection...")

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=16000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Parse JSON response
            # Find JSON block (might be wrapped in markdown)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()

            result = json.loads(json_text)

            print(f"Selected: {len(result.get('selected', []))} papers")
            print(f"Honorable mentions: {len(result.get('honorable_mentions', []))}")

            return result

        except Exception as e:
            print(f"Error processing domain {domain}: {e}")
            return {
                "domain": domain,
                "window_policy_used": "error",
                "stats": {
                    "retrieved": len(papers),
                    "deduped": len(papers),
                    "screened_in": 0,
                    "selected": 0,
                    "strong_threshold": STRONG_PAPER_THRESHOLD
                },
                "selected": [],
                "honorable_mentions": [],
                "notes_ja": [f"処理中にエラーが発生しました: {str(e)}"]
            }

    def _build_scoring_prompt(self, domain: str, papers: List[Dict]) -> str:
        """Build prompt for Claude to score and select papers"""

        # Limit papers to send (avoid overwhelming context)
        papers_to_process = papers[:200]  # Max 200 papers per domain

        papers_json = json.dumps(papers_to_process, indent=2, ensure_ascii=False)

        prompt = f"""あなたは「Literature Radar Orchestrator」として、{domain}分野の最新論文を評価し選定する役割を担います。

# タスク
以下の論文リストから、創薬・トランスレーショナル研究における意思決定に最も重要な論文を最大{MAX_SELECTED}本（最低{MIN_SELECTED}本、強い論文がある場合）選定してください。

# 評価基準（合計100点）
1. **Novelty (0-20点)**: 新規性（新しいタスク・手法・データ・モダリティ）
2. **Breakthrough (0-20点)**: ブレークスルー性（桁違いの改善または新機能）
3. **Future Impact (0-20点)**: 将来的影響（プラットフォーム性・拡張性）
4. **Rigor (0-15点)**: 厳密性（検証・ベンチマーク・サンプルサイズ）
5. **Translational (0-15点)**: トランスレーショナル関連性（標的・バイオマーカー・因果メカニズム）
6. **Community Signal (0-10点)**: コミュニティシグナル（強いジャーナル・著者グループ）

**重要**: 各論文について、スコアの根拠となる **evidence_anchors**（アブストラクトからの逐語的な引用、25単語以内、1-3個）を必ず提供してください。

# 選定制約
- 同一著者グループ: 最大2本
- 同一サブトピック: 最大3本
- 可能であれば、method論文>=3本、application論文>=3本
- Time window優先順位: last_2_days → last_7_days → last_30_days
- Strong paper threshold: Total score >= {STRONG_PAPER_THRESHOLD}

# Window policy
1. last_2_days で strong papers >= {MIN_SELECTED} あれば、そこから選定
2. 不足なら last_7_days に拡大
3. さらに不足なら last_30_days に拡大
4. 使用したポリシーを "window_policy_used" に記録

# Output形式（JSON）
{{
  "domain": "{domain}",
  "window_policy_used": "2d_only|2d_to_7d|2d_to_30d|...",
  "stats": {{
    "retrieved": {len(papers)},
    "deduped": {len(papers)},
    "screened_in": <relevance screening後の数>,
    "selected": <最終選定数>,
    "strong_threshold": {STRONG_PAPER_THRESHOLD}
  }},
  "selected": [
    {{
      "rank": 1,
      "title": "...",
      "date": "YYYY-MM-DD",
      "venue": "...",
      "source": ["EuropePMC", ...],
      "identifiers": {{"doi": null, "pmid": null, "arxiv_id": null}},
      "link": "...",
      "abstract_status": "present|missing",
      "paper_tags": {{
        "paper_type": "method|application|resource|theory",
        "study_stage": "basic|translational|clinical|computational",
        "subtopic": "具体的なサブトピック"
      }},
      "scores": {{
        "novelty": 0-20,
        "breakthrough": 0-20,
        "future_impact": 0-20,
        "rigor": 0-15,
        "translational": 0-15,
        "community_signal": 0-10,
        "total": 0-100
      }},
      "selection_rationale_ja": ["理由1", "理由2"],
      "evidence_anchors": ["verbatim quote 1 (<=25 words)", "verbatim quote 2"],
      "window_used": "last_2_days|last_7_days|last_30_days",
      "summary_ja": {{
        "one_liner": "何の問題を解決したか",
        "whats_new": ["新規性1", "新規性2"],
        "key_results": ["結果1（できれば定量的）", "結果2"],
        "why_it_matters": "創薬・トランスレーショナル研究における意義",
        "method_data": "手法とデータの要点",
        "limitations_risks": ["制限1", "制限2"],
        "next_actions": ["アクション1（オミクス+バイオインフォマティクス創薬支援ビジネスとして）", "アクション2"],
        "speculative_flags": ["推測的記述がある場合リスト"]
      }}
    }}
  ],
  "honorable_mentions": [
    {{
      "title": "...",
      "date": "YYYY-MM-DD",
      "identifiers": {{"doi": null, "pmid": null}},
      "link": "...",
      "reason_ja": "選外理由と簡潔な評価"
    }}
  ],
  "notes_ja": ["ドメイン固有の注記"]
}}

# 重要ルール
- ハルシネーション厳禁。アブストラクトに記載のない数値・主張を創作しない。
- アブストラクトがない場合は "abstract_status": "missing" としてconfidenceを下げる。
- evidence_anchorsは必ずアブストラクトからの逐語的引用（通常英語）。翻訳しない。
- 推測的記述は "speculative_flags" に明記。
- Review論文は除外（include_review_articles=false）。
- JSON以外のテキストは出力しない。

# 入力論文データ
```json
{papers_json}
```

JSON形式で結果を返してください。
"""

        return prompt

    def process_all_domains(self):
        """Process all domains"""
        domains = self.data["domains"]

        for domain, papers in domains.items():
            print(f"\nProcessing {domain}...")
            result = self.score_and_select_domain(domain, papers)
            self.output["domains"].append(result)

        # Global notes
        total_selected = sum(len(d.get("selected", [])) for d in self.output["domains"])
        self.output["global_notes_ja"].append(f"全ドメイン合計選定数: {total_selected}本")

        return self.output

    def json_to_markdown(self, data: Dict) -> str:
        """Convert JSON output to formatted Markdown"""

        md = []

        # Header
        md.append("# 📚 Literature Radar Report\n")
        md.append(f"**Run Date:** {data['run_date_utc']}\n")
        md.append(f"**Time Windows:** {', '.join([w['name'] for w in data['time_windows']])}\n")

        # Summary
        total_selected = sum(len(d.get('selected', [])) for d in data['domains'])
        total_retrieved = sum(d.get('stats', {}).get('retrieved', 0) for d in data['domains'])

        md.append("\n---\n")
        md.append("## 📊 Summary\n")
        md.append(f"- **Total Papers Retrieved:** {total_retrieved}\n")
        md.append(f"- **Total Papers Selected:** {total_selected}\n")
        md.append(f"- **Domains Analyzed:** {len(data['domains'])}\n")

        # Domain breakdown
        md.append("\n### Domain Breakdown\n")
        md.append("| Domain | Retrieved | Selected | Window Policy |\n")
        md.append("|--------|-----------|----------|---------------|\n")

        for domain in data['domains']:
            stats = domain.get('stats', {})
            md.append(f"| {domain['domain']} | {stats.get('retrieved', 0)} | {stats.get('selected', 0)} | {domain.get('window_policy_used', 'N/A')} |\n")

        # Each domain
        for domain_data in data['domains']:
            md.append("\n---\n")
            md.append(f"\n## 🔬 {domain_data['domain']}\n")

            stats = domain_data.get('stats', {})
            md.append(f"\n**Stats:** Retrieved: {stats.get('retrieved', 0)} | Screened: {stats.get('screened_in', 0)} | Selected: {stats.get('selected', 0)}\n")
            md.append(f"**Window Policy:** {domain_data.get('window_policy_used', 'N/A')}\n")

            # Selected papers
            selected = domain_data.get('selected', [])
            if selected:
                md.append(f"\n### 📑 Selected Papers ({len(selected)})\n")

                for paper in selected:
                    md.append(f"\n#### {paper.get('rank', 0)}. {paper.get('title', 'N/A')}\n")

                    # Metadata
                    md.append(f"\n**📅 Date:** {paper.get('date', 'N/A')} | ")
                    md.append(f"**📰 Venue:** {paper.get('venue', 'N/A')} | ")
                    md.append(f"**🔗 Link:** [{paper.get('link', 'N/A')}]({paper.get('link', '#')})\n")

                    identifiers = paper.get('identifiers', {})
                    if identifiers.get('doi'):
                        md.append(f"**DOI:** {identifiers['doi']} | ")
                    if identifiers.get('pmid'):
                        md.append(f"**PMID:** {identifiers['pmid']} | ")
                    if identifiers.get('arxiv_id'):
                        md.append(f"**arXiv:** {identifiers['arxiv_id']} | ")
                    md.append("\n")

                    # Tags
                    tags = paper.get('paper_tags', {})
                    md.append(f"\n**🏷️ Tags:** `{tags.get('paper_type', 'N/A')}` | `{tags.get('study_stage', 'N/A')}` | `{tags.get('subtopic', 'N/A')}`\n")

                    # Scores
                    scores = paper.get('scores', {})
                    md.append(f"\n**📊 Scores** (Total: **{scores.get('total', 0)}**/100)\n")
                    md.append(f"- Novelty: {scores.get('novelty', 0)}/20\n")
                    md.append(f"- Breakthrough: {scores.get('breakthrough', 0)}/20\n")
                    md.append(f"- Future Impact: {scores.get('future_impact', 0)}/20\n")
                    md.append(f"- Rigor: {scores.get('rigor', 0)}/15\n")
                    md.append(f"- Translational: {scores.get('translational', 0)}/15\n")
                    md.append(f"- Community Signal: {scores.get('community_signal', 0)}/10\n")

                    # Rationale
                    rationale = paper.get('selection_rationale_ja', [])
                    if rationale:
                        md.append(f"\n**🎯 選定理由:**\n")
                        for r in rationale:
                            md.append(f"- {r}\n")

                    # Evidence anchors
                    anchors = paper.get('evidence_anchors', [])
                    if anchors:
                        md.append(f"\n**📌 Evidence Anchors:**\n")
                        for anchor in anchors:
                            md.append(f"> {anchor}\n")

                    # Summary
                    summary = paper.get('summary_ja', {})
                    if summary:
                        md.append(f"\n**📝 要約:**\n")

                        if summary.get('one_liner'):
                            md.append(f"\n*{summary['one_liner']}*\n")

                        if summary.get('whats_new'):
                            md.append(f"\n**新規性:**\n")
                            for item in summary['whats_new']:
                                md.append(f"- {item}\n")

                        if summary.get('key_results'):
                            md.append(f"\n**主要結果:**\n")
                            for item in summary['key_results']:
                                md.append(f"- {item}\n")

                        if summary.get('why_it_matters'):
                            md.append(f"\n**重要性:** {summary['why_it_matters']}\n")

                        if summary.get('method_data'):
                            md.append(f"\n**手法・データ:** {summary['method_data']}\n")

                        if summary.get('limitations_risks'):
                            md.append(f"\n**制限事項・リスク:**\n")
                            for item in summary['limitations_risks']:
                                md.append(f"- {item}\n")

                        if summary.get('next_actions'):
                            md.append(f"\n**Next Actions:**\n")
                            for item in summary['next_actions']:
                                md.append(f"- [ ] {item}\n")

                    md.append("\n---\n")

            # Honorable mentions
            mentions = domain_data.get('honorable_mentions', [])
            if mentions:
                md.append(f"\n### 🎖️ Honorable Mentions\n")
                for mention in mentions:
                    md.append(f"\n**{mention.get('title', 'N/A')}**\n")
                    md.append(f"- Date: {mention.get('date', 'N/A')}\n")
                    md.append(f"- Link: [{mention.get('link', 'N/A')}]({mention.get('link', '#')})\n")
                    md.append(f"- Reason: {mention.get('reason_ja', 'N/A')}\n")

            # Notes
            notes = domain_data.get('notes_ja', [])
            if notes:
                md.append(f"\n### 📝 Notes\n")
                for note in notes:
                    md.append(f"- {note}\n")

        # Global notes
        if data.get('global_notes_ja'):
            md.append("\n---\n")
            md.append("\n## 🌐 Global Notes\n")
            for note in data['global_notes_ja']:
                md.append(f"- {note}\n")

        md.append("\n---\n")
        md.append(f"\n*Generated by Literature Radar Orchestrator*\n")

        return "".join(md)

    def save_output(self, output_data: Dict):
        """Save output as Markdown with timestamp filename"""

        # Create output directory if not exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Generate timestamp filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Markdown output only
        md_content = self.json_to_markdown(output_data)
        md_filename = os.path.join(OUTPUT_DIR, f"literature_radar_{timestamp}.md")
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"\n{'='*60}")
        print(f"✅ Output saved:")
        print(f"   Markdown: {md_filename}")
        print(f"{'='*60}")

        return md_filename


def main():
    # Check API key
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        return

    # Load fetched data
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found")
        print("Please run fetch_papers.py first")
        return

    print("Literature Radar - Paper Processor")
    print("="*60)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        fetched_data = json.load(f)

    print(f"Loaded data from: {INPUT_FILE}")
    print(f"Run date: {fetched_data['run_date_utc']}")
    print(f"Fetch timestamp: {fetched_data['fetch_timestamp']}")
    print(f"Domains: {list(fetched_data['domains'].keys())}")
    print("="*60)

    # Process
    processor = PaperProcessor(fetched_data, ANTHROPIC_API_KEY)
    output = processor.process_all_domains()

    # Save
    md_file = processor.save_output(output)

    # Summary
    print("\nProcessing Summary:")
    for domain_result in output["domains"]:
        domain = domain_result["domain"]
        selected = len(domain_result.get("selected", []))
        retrieved = domain_result.get("stats", {}).get("retrieved", 0)
        print(f"  {domain}: {selected}/{retrieved} papers selected")

    print(f"\n📄 View your report:")
    print(f"   {md_file}")


if __name__ == "__main__":
    main()
