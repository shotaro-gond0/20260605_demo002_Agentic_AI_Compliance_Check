"""Gradio UI for Agentic AI Risk Assessment (EU AI Act RAG edition)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import gradio as gr

from file_parser import parse_file
from graph import (
    EU_AI_ACT_URL,
    extract_graph,
    risk_graph,
    AppState,
    ExtractedInfo,
)
import vectorstore as vs

FIELD_KEYS = [
    "overview",
    "users",
    "data_subjects",
    "input_data_categories",
    "output_data_categories",
    "output_purposes",
]

FIELD_LABELS = {
    "overview": "2-1. 概要説明文",
    "users": "2-2. アプリケーション利用者（操作と出力情報の利用者）",
    "data_subjects": "2-3. 入力情報の主体（Data Subject）",
    "input_data_categories": "2-4. 入力情報の情報種（情報カテゴリ）",
    "output_data_categories": "2-5. 出力情報の情報種（情報カテゴリ）",
    "output_purposes": "2-6. 出力情報の利用目的",
}

RISK_ICONS = {
    "禁止": "🚫", "Prohibited": "🚫",
    "高リスク": "🔴", "High-Risk": "🔴",
    "透明性": "🟠", "Transparency": "🟠",
    "限定": "🟡", "Limited": "🟡",
}


def get_risk_icon(level: str) -> str:
    for key, icon in RISK_ICONS.items():
        if key in level:
            return icon
    return "🟢"


# ── EU AI Act Vector Store Update ─────────────────────────────────────────────

def update_eu_ai_act():
    """Fetch EU AI Act PDF and rebuild the FAISS vector store."""
    yield gr.update(
        value=(
            f"⏳ EU AI Act PDFを取得・解析中…\n"
            f"取得元: {EU_AI_ACT_URL}\n"
            f"（PDFは約140ページのため、数十秒かかることがあります）"
        ),
        visible=True,
    )

    chunk_count, err = vs.build_from_url()

    if err:
        yield gr.update(
            value=f"❌ EU AI Actの登録に失敗しました。\n{err}",
            visible=True,
        )
        return

    yield gr.update(
        value=(
            f"✅ EU AI Act ベクトルデータベースを構築しました。\n"
            f"チャンク数: {chunk_count} ／ 取得元: {EU_AI_ACT_URL}\n"
            f"次回以降のリスク評価でRAGによる条文参照が有効になります。"
        ),
        visible=True,
    )


# ── Step 1: Extract ───────────────────────────────────────────────────────────

def run_extraction(file_obj):
    """Parse uploaded file and run LangGraph extraction."""
    if file_obj is None:
        return (
            gr.update(value="⚠️ ファイルが選択されていません。", visible=True),
            *[""] * 6,
            gr.update(visible=False),
            gr.update(visible=False),
        )

    try:
        minutes_text = parse_file(file_obj.name, os.path.basename(file_obj.name))
    except Exception as e:
        return (
            gr.update(value=f"❌ ファイル読み込みエラー: {e}", visible=True),
            *[""] * 6,
            gr.update(visible=False),
            gr.update(visible=False),
        )

    if not minutes_text.strip():
        return (
            gr.update(
                value="❌ テキストを抽出できませんでした。別のファイルをお試しください。",
                visible=True,
            ),
            *[""] * 6,
            gr.update(visible=False),
            gr.update(visible=False),
        )

    initial_state: AppState = {
        "minutes_text": minutes_text,
        "extracted": None,
        "edited": None,
        "eu_ai_act_text": None,
        "risk": None,
        "error": None,
    }

    try:
        result = extract_graph.invoke(initial_state)
    except Exception as e:
        return (
            gr.update(value=f"❌ 情報抽出エラー: {e}", visible=True),
            *[""] * 6,
            gr.update(visible=False),
            gr.update(visible=False),
        )

    if result.get("error"):
        return (
            gr.update(value=f"❌ エラー: {result['error']}", visible=True),
            *[""] * 6,
            gr.update(visible=False),
            gr.update(visible=False),
        )

    extracted = result["extracted"]
    values = [extracted.get(k, "") for k in FIELD_KEYS]

    return (
        gr.update(
            value="✅ 情報抽出が完了しました。内容を確認・編集してからリスク評価を実行してください。",
            visible=True,
        ),
        *values,
        gr.update(visible=True),   # edit_section
        gr.update(visible=False),  # result_section
    )


# ── Step 2: Risk Assessment ───────────────────────────────────────────────────

def run_risk_assessment(overview, users, data_subjects, input_cats, output_cats, purposes):
    """
    LangGraph risk flow:
      fetch_eu_ai_act_node  — multi-query RAG retrieval from FAISS vector store
      risk_assess_node      — LLM judges risk using ONLY retrieved chunks
    """
    if not any([overview, users, data_subjects, input_cats, output_cats, purposes]):
        return (
            gr.update(
                value="⚠️ まずファイルをアップロードして情報を抽出してください。",
                visible=True,
            ),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    if not vs.is_ready():
        return (
            gr.update(
                value=(
                    "⚠️ EU AI Actのベクトルデータベースが未登録です。\n"
                    "画面上部の「🔄 EU AI Actの情報を更新する」ボタンを先に押してください。"
                ),
                visible=True,
            ),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    edited: ExtractedInfo = {
        "overview": overview,
        "users": users,
        "data_subjects": data_subjects,
        "input_data_categories": input_cats,
        "output_data_categories": output_cats,
        "output_purposes": purposes,
    }

    state: AppState = {
        "minutes_text": "",
        "extracted": None,
        "edited": edited,
        "eu_ai_act_text": None,
        "risk": None,
        "error": None,
    }

    try:
        result = risk_graph.invoke(state)
    except Exception as e:
        return (
            gr.update(value=f"❌ リスク評価エラー: {e}", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    if result.get("error"):
        return (
            gr.update(value=f"❌ {result['error']}", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    risk = result.get("risk")
    if not risk:
        return (
            gr.update(value="❌ リスク評価結果が得られませんでした。", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    level = risk.get("risk_level", "不明")
    basis = risk.get("risk_basis", "")
    icon = get_risk_icon(level)

    result_md = f"""## {icon} EU AI Act リスクレベル判定結果

### リスクレベル
**{level}**

### 判定根拠

{basis}

---
*判定根拠: EU AI Act公式PDFから構築したRAGベクトルデータベースの検索結果のみを使用*
*出典: [Regulation (EU) 2024/1689]({EU_AI_ACT_URL})*
"""

    return (
        gr.update(
            value=(
                "✅ リスク評価が完了しました。\n"
                "（RAGベクトルデータベースから関連条文を取得して判定）"
            ),
            visible=True,
        ),
        gr.update(value=result_md, visible=True),
        gr.update(visible=True),
    )


# ── Gradio UI ─────────────────────────────────────────────────────────────────

CSS = """
#title { text-align: center; }
.field-box textarea { min-height: 80px; }
.update-btn { background: #0f4c81 !important; }
"""

with gr.Blocks(title="Agentic AI リスク評価ツール") as demo:

    # ── Header ────────────────────────────────────────────────────────────────
    gr.Markdown(
        """# 🤖 Agentic AI リスク評価ツール

議事録ファイルから Agentic AI アプリケーション情報を抽出し、
**EU AI Act（Regulation (EU) 2024/1689）** の条文をRAGで参照してリスクレベルを判定します。

---""",
        elem_id="title",
    )

    # ── EU AI Act Vector Store Section ────────────────────────────────────────
    gr.Markdown("## 🗄️ EU AI Act ドキュメント登録（RAGベクトルDB）")
    gr.Markdown(
        f"リスク評価の前に、EU AI Act の最新PDFをベクトルデータベースに登録してください。\n\n"
        f"登録元: [`{EU_AI_ACT_URL}`]({EU_AI_ACT_URL})"
    )

    with gr.Row():
        update_btn = gr.Button(
            "🔄 EU AI Actの情報を更新する",
            variant="primary",
            scale=1,
            min_width=280,
            elem_classes=["update-btn"],
        )
        update_status = gr.Textbox(
            label="登録ステータス",
            value="⚠️ 未登録 — 「🔄 EU AI Actの情報を更新する」を押してください。",
            interactive=False,
            scale=3,
            visible=True,
        )

    gr.Markdown("---")

    # ── General Status ────────────────────────────────────────────────────────
    status = gr.Textbox(label="ステータス", interactive=False, visible=False)

    # ── Step 1: File Upload ───────────────────────────────────────────────────
    gr.Markdown("## 📁 ステップ 1 : 議事録ファイルのアップロード")
    gr.Markdown(
        "対応フォーマット: **Microsoft Word** (.docx) / **PDF** (.pdf) / **テキスト** (.txt)"
    )

    with gr.Row():
        file_input = gr.File(
            label="議事録ファイルを選択",
            file_types=[".docx", ".pdf", ".txt", ".text"],
            scale=4,
        )
        extract_btn = gr.Button(
            "📄 情報を抽出する",
            variant="primary",
            scale=1,
            min_width=160,
        )

    # ── Step 2: Editable Fields ───────────────────────────────────────────────
    with gr.Group(visible=False) as edit_section:
        gr.Markdown("## ✏️ ステップ 2 : 抽出結果の確認・編集")
        gr.Markdown(
            "抽出された内容を確認し、必要に応じて各フィールドを直接編集してください。"
            "編集後、**「リスク評価を実行する」** ボタンを押してください。"
        )

        field_boxes = []
        for key in FIELD_KEYS:
            tb = gr.Textbox(
                label=FIELD_LABELS[key],
                lines=3,
                interactive=True,
                elem_classes=["field-box"],
            )
            field_boxes.append(tb)

        gr.Markdown(
            "> ⚖️ リスク評価を実行すると、**サブエージェント（fetch_eu_ai_act_node）** が "
            "上記RAGベクトルDBからArticle 5 / 6 / 50 の関連条文を取得し、"
            "その内容のみを根拠として判定します。"
        )
        assess_btn = gr.Button(
            "⚖️ リスク評価を実行する（RAG + EU AI Act 条文のみで判定）",
            variant="primary",
            size="lg",
        )

    # ── Step 3: Risk Result ───────────────────────────────────────────────────
    with gr.Group(visible=False) as result_section:
        gr.Markdown("## 📊 ステップ 3 : EU AI Act リスクレベル判定結果")
        result_md = gr.Markdown()

    # ── Event Bindings ────────────────────────────────────────────────────────
    update_btn.click(
        fn=update_eu_ai_act,
        inputs=[],
        outputs=[update_status],
    )

    extract_btn.click(
        fn=run_extraction,
        inputs=[file_input],
        outputs=[status, *field_boxes, edit_section, result_section],
    )

    assess_btn.click(
        fn=run_risk_assessment,
        inputs=field_boxes,
        outputs=[status, result_md, result_section],
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="blue"),
        css=CSS,
    )
