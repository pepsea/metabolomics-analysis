#!/usr/bin/env python3
"""
Literature Radar - Web Interface (Streamlit)
iPadから使えるWebアプリ版
"""

import streamlit as st
import json
import os
from datetime import datetime
import subprocess
import tempfile

st.set_page_config(
    page_title="Literature Radar",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Literature Radar Orchestrator")
st.markdown("オミクス・バイオインフォマティクス論文の自動収集・評価システム")

# Sidebar: Configuration
st.sidebar.header("⚙️ Configuration")

preset = st.sidebar.selectbox(
    "Preset",
    ["default", "quick", "comprehensive", "weekly", "monthly",
     "metabolomics_only", "ai_focus"],
    help="事前定義された設定を選択"
)

api_key = st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    value=os.environ.get("ANTHROPIC_API_KEY", ""),
    help="Anthropic APIキーを入力"
)

# Main area
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Domains", "8")
with col2:
    st.metric("Data Sources", "5")
with col3:
    st.metric("Preset", preset)

st.markdown("---")

# Run button
if st.button("🚀 Run Literature Radar", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ APIキーを入力してください")
    else:
        with st.spinner("論文を収集中..."):
            # Set API key
            os.environ["ANTHROPIC_API_KEY"] = api_key

            # Progress tracking
            progress_bar = st.progress(0)
            status = st.empty()

            # Step 1: Generate config
            status.text("📝 設定ファイルを生成中...")
            try:
                subprocess.run(
                    ["python3", "generate_config.py", preset],
                    check=True,
                    capture_output=True
                )
                progress_bar.progress(10)
            except subprocess.CalledProcessError as e:
                st.error(f"設定生成エラー: {e}")
                st.stop()

            # Step 2: Fetch papers
            status.text("📥 論文を収集中（1-3分）...")
            try:
                result = subprocess.run(
                    ["python3", "fetch_papers.py"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                progress_bar.progress(50)

                # Show fetch summary
                with st.expander("📊 収集結果"):
                    st.code(result.stdout)

            except subprocess.CalledProcessError as e:
                st.error(f"論文収集エラー: {e}")
                st.error(e.stderr)
                st.stop()
            except subprocess.TimeoutExpired:
                st.error("タイムアウト: 論文収集に時間がかかりすぎています")
                st.stop()

            # Step 3: Process papers
            status.text("🤖 Claude APIで評価中（3-10分）...")
            try:
                result = subprocess.run(
                    ["python3", "process_papers.py"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=900
                )
                progress_bar.progress(100)
                status.text("✅ 完了！")

                # Show processing summary
                with st.expander("📈 処理結果"):
                    st.code(result.stdout)

            except subprocess.CalledProcessError as e:
                st.error(f"論文処理エラー: {e}")
                st.error(e.stderr)
                st.stop()
            except subprocess.TimeoutExpired:
                st.error("タイムアウト: 論文処理に時間がかかりすぎています")
                st.stop()

            # Success
            st.success("🎉 レポート生成完了！")

            # Find latest output
            output_files = sorted(
                [f for f in os.listdir("outputs") if f.endswith(".md")],
                reverse=True
            )

            if output_files:
                latest_md = output_files[0]
                latest_json = latest_md.replace(".md", ".json")

                # Display results
                st.markdown("---")
                st.subheader("📄 生成されたレポート")

                col1, col2 = st.columns(2)

                with col1:
                    # Download Markdown
                    with open(f"outputs/{latest_md}", "r", encoding="utf-8") as f:
                        md_content = f.read()

                    st.download_button(
                        label="📥 Markdownをダウンロード",
                        data=md_content,
                        file_name=latest_md,
                        mime="text/markdown",
                        use_container_width=True
                    )

                with col2:
                    # Download JSON
                    with open(f"outputs/{latest_json}", "r", encoding="utf-8") as f:
                        json_content = f.read()

                    st.download_button(
                        label="📥 JSONをダウンロード",
                        data=json_content,
                        file_name=latest_json,
                        mime="application/json",
                        use_container_width=True
                    )

                # Preview
                st.markdown("---")
                st.subheader("👀 プレビュー")

                # Show first 2000 characters
                with st.expander("Markdownプレビュー（一部）", expanded=True):
                    st.markdown(md_content[:2000] + "\n\n*(続きはダウンロードして確認)*")

# History
st.markdown("---")
st.subheader("📚 過去のレポート")

if os.path.exists("outputs"):
    output_files = sorted(
        [f for f in os.listdir("outputs") if f.endswith(".md")],
        reverse=True
    )

    if output_files:
        for i, filename in enumerate(output_files[:10]):  # Show last 10
            timestamp = filename.replace("literature_radar_", "").replace(".md", "")

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.text(f"📄 {filename}")

            with col2:
                with open(f"outputs/{filename}", "r", encoding="utf-8") as f:
                    md_content = f.read()
                st.download_button(
                    label="MD",
                    data=md_content,
                    file_name=filename,
                    mime="text/markdown",
                    key=f"md_{i}"
                )

            with col3:
                json_filename = filename.replace(".md", ".json")
                if os.path.exists(f"outputs/{json_filename}"):
                    with open(f"outputs/{json_filename}", "r", encoding="utf-8") as f:
                        json_content = f.read()
                    st.download_button(
                        label="JSON",
                        data=json_content,
                        file_name=json_filename,
                        mime="application/json",
                        key=f"json_{i}"
                    )
    else:
        st.info("まだレポートが生成されていません")
else:
    st.info("outputsディレクトリが見つかりません")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <small>Literature Radar Orchestrator v1.1 | Powered by Claude 4.5</small>
</div>
""", unsafe_allow_html=True)
