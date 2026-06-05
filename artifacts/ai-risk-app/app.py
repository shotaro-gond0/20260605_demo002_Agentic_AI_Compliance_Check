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
    fetch_eu_ai_act_node,
    risk_assess_node,
    AppState,
    ExtractedInfo,
)
import vectorstore as vs
from pdf_report import generate_pdf

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
    """Fetch EU AI Act articles from the web and rebuild the FAISS vector store."""
    yield gr.update(
        value=(
            f"⏳ EU AI Act 全条文（第1条〜第113条）を取得中…\n"
            f"取得元: {vs.EU_AI_ACT_SOURCE_URL}\n"
            f"（約113ページ分の並列取得のため、30〜60秒かかることがあります）"
        ),
        visible=True,
    )

    chunk_count, err = vs.build_from_web()

    if err:
        yield gr.update(
            value=f"❌ EU AI Actの登録に失敗しました。\n{err}",
            visible=True,
        )
        return

    yield gr.update(
        value=(
            f"✅ EU AI Act ベクトルデータベースを構築しました。\n"
            f"チャンク数: {chunk_count} ／ 取得元: {vs.EU_AI_ACT_SOURCE_URL}\n"
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

def _no_yield(msg: str):
    """Helper: single-yield tuple for early-exit error cases (5 outputs)."""
    return (
        gr.update(value=msg, visible=True),
        gr.update(value="", visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        None,  # report_state
    )


def run_risk_assessment(overview, users, data_subjects, input_cats, output_cats, purposes):
    """Generator: yields step-by-step status so the UI updates at each node boundary.

    Outputs (5):  status | llm_status | result_md | result_section | report_state
    Nodes called directly (not via risk_graph.invoke) to enable per-step yields:
      1. fetch_eu_ai_act_node — RAG retrieval from FAISS
      2. risk_assess_node     — GPT-4o API call
    """
    # ── Pre-flight checks ─────────────────────────────────────────────────────
    if not any([overview, users, data_subjects, input_cats, output_cats, purposes]):
        yield _no_yield("⚠️ まずファイルをアップロードして情報を抽出してください。")
        return

    if not vs.is_ready():
        yield _no_yield(
            "⚠️ EU AI Actのベクトルデータベースが未登録です。\n"
            "画面上部の「🔄 EU AI Actの情報を更新する」ボタンを先に押してください。"
        )
        return

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

    # ── Node 1: fetch_eu_ai_act_node（RAG検索）────────────────────────────────
    yield (
        gr.update(value="⏳ リスク評価を開始します…", visible=True),
        gr.update(
            value="[ 1 / 2 ]  fetch_eu_ai_act_node — RAGベクトルDBを検索中…",
            visible=True,
        ),
        gr.update(visible=False),
        gr.update(visible=False),
        None,
    )

    try:
        state = fetch_eu_ai_act_node(state)
    except Exception as e:
        yield _no_yield(f"❌ RAG検索エラー: {e}")
        return

    if state.get("error"):
        yield _no_yield(f"❌ {state['error']}")
        return

    # ── Node 2: risk_assess_node（GPT-4o API呼び出し）────────────────────────
    yield (
        gr.update(value="⏳ RAG検索完了 — LLMに送信中…", visible=True),
        gr.update(
            value=(
                "[ 1 / 2 ]  fetch_eu_ai_act_node — ✅ 完了\n"
                "[ 2 / 2 ]  risk_assess_node — GPT-4o (gpt-4o / temperature=0) に"
                "RAG条文テキストとアプリ情報を送信中…"
            ),
            visible=True,
        ),
        gr.update(visible=False),
        gr.update(visible=False),
        None,
    )

    try:
        state = risk_assess_node(state)
    except Exception as e:
        yield _no_yield(f"❌ LLM API呼び出しエラー: {e}")
        return

    if state.get("error"):
        yield _no_yield(f"❌ {state['error']}")
        return

    # ── 結果表示 ──────────────────────────────────────────────────────────────
    risk = state.get("risk")
    if not risk:
        yield _no_yield("❌ リスク評価結果が得られませんでした。")
        return

    level = risk.get("risk_level", "不明")
    basis = risk.get("risk_basis", "")
    icon = get_risk_icon(level)

    md = f"""## {icon} EU AI Act リスクレベル判定結果

### リスクレベル
**{level}**

### 判定根拠

{basis}

---
*判定根拠: EU AI Act公式PDFから構築したRAGベクトルデータベースの検索結果のみを使用*
*出典: [Regulation (EU) 2024/1689]({EU_AI_ACT_URL})*
"""

    report_state = {
        "risk_level": level,
        "risk_basis": basis,
        "overview": overview,
        "users": users,
        "data_subjects": data_subjects,
        "input_cats": input_cats,
        "output_cats": output_cats,
        "purposes": purposes,
    }

    yield (
        gr.update(value="✅ リスク評価が完了しました。", visible=True),
        gr.update(
            value=(
                "[ 1 / 2 ]  fetch_eu_ai_act_node — ✅ 完了\n"
                "[ 2 / 2 ]  risk_assess_node — ✅ 完了  GPT-4o の応答を受信し、リスクレベルを判定しました。"
            ),
            visible=True,
        ),
        gr.update(value=md, visible=True),
        gr.update(visible=True),
        report_state,
    )


# ── Step 3: PDF Download ───────────────────────────────────────────────────────

def download_report(report_state):
    """Generator: yields step-by-step status during PDF generation and file delivery.

    Outputs (3):  report_file | download_status | status
    Steps:
      1. generate_pdf()   — fpdf2 でPDFをメモリ上に構築し一時ファイルへ書き出す
      2. gr.File(value=)  — Gradio がブラウザへファイルを配信できる状態にする
    """
    if not report_state:
        yield (
            gr.update(value="", visible=False),
            gr.update(value="⚠️ 先にリスク評価を実行してください。", visible=True),
            gr.update(value="⚠️ レポートを生成する前にリスク評価を実行してください。", visible=True),
        )
        return

    # ── Step 1: generate_pdf() ────────────────────────────────────────────────
    yield (
        gr.update(value="", visible=False),
        gr.update(
            value="[ 1 / 2 ]  generate_pdf() — fpdf2 でPDFを構築中…",
            visible=True,
        ),
        gr.update(value="⏳ PDFを生成中…", visible=True),
    )

    try:
        path = generate_pdf(
            risk_level=report_state.get("risk_level", "不明"),
            risk_basis=report_state.get("risk_basis", ""),
            overview=report_state.get("overview", ""),
            users=report_state.get("users", ""),
            data_subjects=report_state.get("data_subjects", ""),
            input_cats=report_state.get("input_cats", ""),
            output_cats=report_state.get("output_cats", ""),
            purposes=report_state.get("purposes", ""),
            eu_ai_act_url=EU_AI_ACT_URL,
        )
    except Exception as e:
        yield (
            gr.update(value="", visible=False),
            gr.update(value=f"❌ PDF生成エラー: {e}", visible=True),
            gr.update(value=f"❌ PDFレポートの生成に失敗しました: {e}", visible=True),
        )
        return

    # ── Step 2: ダウンロードリンク生成 ────────────────────────────────────────
    import os as _os
    filename = _os.path.basename(path)
    download_html = (
        f'<div style="padding:12px 16px;background:#f0f9ff;border:1px solid #bae6fd;'
        f'border-radius:8px;margin-top:4px;">'
        f'<a href="/file={path}" download="{filename}" '
        f'style="color:#0369a1;text-decoration:none;font-weight:600;'
        f'display:flex;align-items:center;gap:8px;font-size:1em;">'
        f'📄 {filename}'
        f'<span style="font-size:0.82em;color:#64748b;font-weight:400;">'
        f'　← クリックしてダウンロード</span>'
        f'</a></div>'
    )

    yield (
        gr.update(value=download_html, visible=True),
        gr.update(
            value=(
                "[ 1 / 2 ]  generate_pdf() — ✅ 完了\n"
                "[ 2 / 2 ]  PDFレポートの準備が完了しました。ファイル名をクリックしてダウンロードしてください。"
            ),
            visible=True,
        ),
        gr.update(value="✅ PDFレポートの準備が完了しました。", visible=True),
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
        f"リスク評価の前に、EU AI Act の最新条文をベクトルデータベースに登録してください。\n\n"
        f"登録元: [`{vs.EU_AI_ACT_SOURCE_URL}`]({vs.EU_AI_ACT_SOURCE_URL})"
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
            value=(
                "✅ 既存インデックスを読み込みました — すぐにリスク評価が利用可能です。"
                if vs.was_loaded_from_disk()
                else "⚠️ 未登録 — 「🔄 EU AI Actの情報を更新する」を押してください。"
            ),
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

        llm_status = gr.Textbox(
            label="🔄 処理ステータス（LangGraph ノード進捗）",
            interactive=False,
            lines=2,
            visible=False,
        )

    # ── Step 3: Risk Result ───────────────────────────────────────────────────
    report_state = gr.State(None)

    with gr.Group(visible=False) as result_section:
        gr.Markdown("## 📊 ステップ 3 : EU AI Act リスクレベル判定結果")
        result_md = gr.Markdown()

        with gr.Row():
            download_btn = gr.Button(
                "📥 レポートをダウンロード（PDF）",
                variant="secondary",
                scale=1,
                min_width=220,
            )

        download_status = gr.Textbox(
            label="🔄 PDF生成ステータス",
            interactive=False,
            lines=2,
            visible=False,
        )

        report_link = gr.HTML(visible=False)

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
        outputs=[status, llm_status, result_md, result_section, report_state],
    )

    download_btn.click(
        fn=download_report,
        inputs=[report_state],
        outputs=[report_link, download_status, status],
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="blue"),
        css=CSS,
        allowed_paths=["/tmp"],
    )
