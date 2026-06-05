"""Chainlit UI for Agentic AI Risk Assessment."""
from __future__ import annotations

import chainlit as cl
from chainlit.input_widget import TextInput

from file_parser import parse_file
from graph import extract_graph, risk_graph, AppState

FIELD_LABELS = {
    "overview": "2-1. 概要説明文",
    "users": "2-2. アプリケーション利用者（操作と出力情報の利用者）",
    "data_subjects": "2-3. 入力情報の主体（Data Subject）",
    "input_data_categories": "2-4. 入力情報の情報種（情報カテゴリ）",
    "output_data_categories": "2-5. 出力情報の情報種（情報カテゴリ）",
    "output_purposes": "2-6. 出力情報の利用目的",
}
FIELD_KEYS = list(FIELD_LABELS.keys())


def get_state() -> AppState:
    return cl.user_session.get("app_state") or {}


def set_state(state: AppState):
    cl.user_session.set("app_state", state)


def get_phase() -> str:
    return cl.user_session.get("phase", "upload")


def set_phase(phase: str):
    cl.user_session.set("phase", phase)


@cl.on_chat_start
async def on_start():
    set_phase("upload")
    await cl.Message(
        content=(
            "# 🤖 Agentic AI リスク評価ツール\n\n"
            "このツールは議事録から **Agentic AIアプリケーション** に関する情報を抽出し、"
            "**EU AI Act（Regulation (EU) 2024/1689）** に基づくリスクレベルを判定します。\n\n"
            "---\n"
            "### 📁 ステップ1: 議事録ファイルのアップロード\n\n"
            "対応フォーマット:\n"
            "- **Microsoft Word** (.docx)\n"
            "- **PDF** (.pdf)\n"
            "- **テキスト** (.txt / .text)\n\n"
            "💡 ファイルをこのチャットに添付してアップロードしてください。"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    phase = get_phase()

    if phase == "upload":
        await _handle_upload(message)
    elif phase == "editing":
        await _handle_editing(message)
    else:
        await cl.Message(
            content="新しい評価を行う場合は、ページを更新してください。"
        ).send()


async def _handle_upload(message: cl.Message):
    files = message.elements
    if not files:
        await cl.Message(
            content=(
                "⚠️ ファイルが添付されていません。\n\n"
                "Word (.docx)、PDF (.pdf)、またはテキスト (.txt) ファイルを添付してください。"
            )
        ).send()
        return

    file = files[0]
    filename = file.name

    await cl.Message(content=f"📄 **{filename}** を受け取りました。テキストを抽出中...").send()

    try:
        minutes_text = parse_file(file.path, filename)
    except Exception as e:
        await cl.Message(content=f"❌ ファイルの読み込みに失敗しました:\n```\n{e}\n```").send()
        return

    if not minutes_text.strip():
        await cl.Message(
            content="❌ ファイルからテキストを抽出できませんでした。別のファイルをお試しください。"
        ).send()
        return

    await cl.Message(
        content=(
            f"✅ テキスト抽出完了（{len(minutes_text):,} 文字）\n\n"
            "🔍 **Agentic AI関連情報を抽出中...** GPT-4oで解析しています。少々お待ちください。"
        )
    ).send()

    initial_state: AppState = {
        "minutes_text": minutes_text,
        "extracted": None,
        "edited": None,
        "risk": None,
        "error": None,
    }

    try:
        async with cl.Step(name="LangGraph: 議事録解析・情報抽出") as step:
            result = extract_graph.invoke(initial_state)
            step.output = "✅ 情報抽出が完了しました"
    except Exception as e:
        await cl.Message(content=f"❌ 情報抽出中にエラーが発生しました:\n```\n{e}\n```").send()
        return

    if result.get("error"):
        await cl.Message(content=f"❌ エラー: {result['error']}").send()
        return

    set_state(result)
    set_phase("editing")
    await _show_edit_form(result["extracted"])


async def _show_edit_form(extracted: dict):
    await cl.Message(
        content=(
            "## ✅ ステップ2・3: 抽出結果の確認・編集\n\n"
            "以下は議事録から抽出した情報です。\n"
            "右上の ⚙️（設定）アイコンをクリックすると、各項目を編集できます。\n\n"
            "編集が完了したら、このチャットに **`OK`** または **`送信`** と入力してください。"
        )
    ).send()

    widgets = [
        TextInput(
            id=key,
            label=FIELD_LABELS[key],
            initial=extracted.get(key, ""),
            multiline=True,
        )
        for key in FIELD_KEYS
    ]

    await cl.ChatSettings(widgets).send()

    await cl.Message(
        content=(
            "---\n"
            "**現在の抽出内容（プレビュー）:**\n\n"
            + "\n\n".join(
                f"**{FIELD_LABELS[k]}**\n> {extracted.get(k, '（未入力）')}"
                for k in FIELD_KEYS
            )
            + "\n\n---\n"
            "⬆️ 上記の内容を確認し、必要に応じて ⚙️ から編集してください。\n"
            "完了したら **`OK`** または **`送信`** と入力してください。"
        )
    ).send()


@cl.on_settings_update
async def on_settings_update(settings: dict):
    cl.user_session.set("current_settings", settings)


async def _handle_editing(message: cl.Message):
    text = message.content.strip().lower()
    confirm_words = {"ok", "送信", "submit", "完了", "done", "yes", "はい", "確定", "実行"}
    if text not in confirm_words:
        await cl.Message(
            content=(
                "💡 内容を編集後、**`OK`** または **`送信`** と入力してリスク評価を開始してください。\n"
                "（⚙️ ボタンから各項目を編集できます）"
            )
        ).send()
        return

    settings = cl.user_session.get("current_settings") or {}
    state = get_state()
    original = state.get("extracted") or {}

    edited = {
        key: settings.get(key, original.get(key, ""))
        for key in FIELD_KEYS
    }
    state["edited"] = edited
    set_state(state)

    edited_summary = "\n\n".join(
        f"**{FIELD_LABELS[k]}**\n{edited[k] or '（未入力）'}"
        for k in FIELD_KEYS
    )
    await cl.Message(
        content=f"## 📝 ステップ3: 編集確定内容\n\n{edited_summary}"
    ).send()

    await cl.Message(
        content=(
            "⚖️ **ステップ4: EU AI Act リスクレベルを判定中...**\n"
            "第5条・第6条・第50条に基づいて評価しています。少々お待ちください。"
        )
    ).send()

    try:
        async with cl.Step(name="LangGraph: EU AI Act リスク評価") as step:
            result = risk_graph.invoke(state)
            step.output = "✅ リスク評価が完了しました"
    except Exception as e:
        await cl.Message(content=f"❌ リスク評価中にエラーが発生しました:\n```\n{e}\n```").send()
        return

    if result.get("error"):
        await cl.Message(content=f"❌ エラー: {result['error']}").send()
        return

    set_state(result)
    set_phase("done")
    await _show_risk_result(result["risk"])


async def _show_risk_result(risk: dict):
    level = risk.get("risk_level", "不明")
    basis = risk.get("risk_basis", "")

    if "禁止" in level:
        icon = "🚫"
    elif "高リスク" in level or "High-Risk" in level:
        icon = "🔴"
    elif "透明性" in level or "Transparency" in level:
        icon = "🟠"
    elif "限定" in level or "Limited" in level:
        icon = "🟡"
    else:
        icon = "🟢"

    await cl.Message(
        content=(
            f"---\n"
            f"## {icon} ステップ4・5: EU AI Act リスクレベル判定結果\n\n"
            f"### リスクレベル\n"
            f"**{level}**\n\n"
            f"### 判定根拠（第6条中心）\n\n"
            f"{basis}\n\n"
            f"---\n"
            f"### 参照条文\n"
            f"- **第5条 (Article 5)**: Prohibited artificial intelligence practices（禁止されるAIの実践）\n"
            f"- **第6条 (Article 6)**: Classification rules for high-risk AI systems（高リスクAIシステムの分類規則）\n"
            f"- **第50条 (Article 50)**: Transparency obligations for providers and deployers（透明性義務）\n\n"
            f"*出典: EU AI Act — Regulation (EU) 2024/1689*\n\n"
            f"---\n"
            f"💡 別の議事録を評価する場合は、ページを更新して新しいチャットを開始してください。"
        )
    ).send()
