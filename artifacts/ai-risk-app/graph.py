"""LangGraph workflow for Agentic AI Risk Assessment.

Risk graph (called on every risk assessment run):
  START → fetch_eu_ai_act → (error?) → risk_assess → END
                           ↘ error_node → END

fetch_eu_ai_act_node: retrieves relevant EU AI Act chunks from the in-memory
  FAISS vector store (populated via the Gradio "更新" button).
  Uses multi-query RAG to cover Article 5 / 6 / 50 + application context.

risk_assess_node: receives retrieved chunks via state.eu_ai_act_text and
  uses ONLY that text as grounding for the LLM risk judgment.
"""
from __future__ import annotations

import json
from typing import TypedDict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

import vectorstore as vs

EU_AI_ACT_URL = vs.EU_AI_ACT_URL


# ── State ─────────────────────────────────────────────────────────────────────

class ExtractedInfo(TypedDict):
    overview: str
    users: str
    data_subjects: str
    input_data_categories: str
    output_data_categories: str
    output_purposes: str


class RiskAssessment(TypedDict):
    risk_level: str
    risk_basis: str


class AppState(TypedDict):
    minutes_text: str
    extracted: Optional[ExtractedInfo]
    edited: Optional[ExtractedInfo]
    eu_ai_act_text: Optional[str]   # RAG-retrieved chunks for this run
    risk: Optional[RiskAssessment]
    error: Optional[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) >= 3 else parts[-1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _build_rag_queries(edited: ExtractedInfo) -> list[str]:
    """Construct multi-query list for vector store retrieval."""
    app_context = (
        f"AI system: {edited.get('overview', '')} "
        f"users: {edited.get('users', '')} "
        f"data subjects: {edited.get('data_subjects', '')} "
        f"input data: {edited.get('input_data_categories', '')} "
        f"output data: {edited.get('output_data_categories', '')} "
        f"purpose: {edited.get('output_purposes', '')}"
    )
    return [
        app_context,
        "Article 5 prohibited artificial intelligence practices biometric categorisation real-time remote identification",
        "Article 6 classification rules high-risk AI systems Annex III safety component",
        "Article 50 transparency obligations providers deployers general-purpose AI model",
        "high-risk AI system requirements obligations conformity assessment",
    ]


# ── Prompts ───────────────────────────────────────────────────────────────────

EXTRACT_SYSTEM = """あなたは議事録を解析し、Agentic AIアプリケーションの開発・利用に関する情報を抽出する専門家です。
議事録テキストから以下の6項目を日本語で抽出・要約してください。
議事録にAgentic AIアプリケーションに関する記載がない場合は、各項目に「記載なし」と返してください。

必ずJSONのみを返してください（コードブロック不要）:
{
  "overview": "概要説明文",
  "users": "アプリケーション利用者（操作と出力情報の利用者）",
  "data_subjects": "入力情報の主体（Data Subject）",
  "input_data_categories": "入力情報の情報種（情報カテゴリ）",
  "output_data_categories": "出力情報の情報種（情報カテゴリ）",
  "output_purposes": "出力情報の利用目的"
}"""

RISK_SYSTEM_TEMPLATE = """あなたはEU AI Actの条文を厳密に解釈する法律専門家です。

以下の【EU AI Act 条文テキスト（RAG取得）】は、EU AI Act公式PDF
（{url}）から構築したベクトルデータベースに対して
関連性の高いチャンクを検索・取得したものです。

このテキストの内容だけを根拠として、提供されたAgentic AIアプリケーションの
リスクレベルを判定してください。

制約:
- 条文テキスト以外の知識・推測を使用しないこと
- 条文テキストに判定根拠が見当たらない場合はその旨を明記すること
- 第6条（Article 6）の内容を主な判定根拠とすること

リスクレベルの選択肢:
1. 「禁止（Prohibited）」: Article 5 に該当
2. 「高リスク（High-Risk）」: Article 6 に該当
3. 「透明性義務あり（Transparency Obligation）」: Article 50 のみ適用
4. 「限定リスク（Limited Risk）」: 上記に該当しないが義務あり
5. 「最小リスク（Minimal Risk）」: 規制上の義務がほとんどない

必ずJSONのみを返してください（コードブロック不要）:
{{
  "risk_level": "リスクレベル名",
  "risk_basis": "判定根拠（引用した条文箇所を明示しながら詳細に説明）"
}}

【EU AI Act 条文テキスト（RAG取得）】
{eu_ai_act_text}
"""


# ── Graph Nodes ───────────────────────────────────────────────────────────────

def extract_node(state: AppState) -> AppState:
    """Extract Agentic AI info from meeting minutes text."""
    llm = make_llm()
    messages = [
        SystemMessage(content=EXTRACT_SYSTEM),
        HumanMessage(
            content=f"以下の議事録テキストを解析してください:\n\n{state['minutes_text']}"
        ),
    ]
    response = llm.invoke(messages)
    data = json.loads(_strip_fences(response.content))
    return {**state, "extracted": ExtractedInfo(**data)}


def fetch_eu_ai_act_node(state: AppState) -> AppState:
    """Sub-agent: retrieve EU AI Act context via RAG from the FAISS vector store.

    Checks that the vector store is initialized (user must click "更新" first),
    then runs multi-query retrieval and stores results in state.eu_ai_act_text.
    """
    if not vs.is_ready():
        return {
            **state,
            "error": (
                "EU AI Actのベクトルデータベースが未登録です。\n"
                "画面上部の「🔄 EU AI Actの情報を更新する」ボタンをクリックして、"
                "まずドキュメントを登録してください。"
            ),
        }

    edited = state.get("edited") or state.get("extracted")
    if not edited:
        return {**state, "error": "評価対象の情報が見つかりません。"}

    queries = _build_rag_queries(edited)
    retrieved_text = vs.retrieve(queries, k_per_query=6)

    if not retrieved_text.strip():
        return {
            **state,
            "error": (
                "ベクトルデータベースから関連条文を取得できませんでした。\n"
                "「🔄 EU AI Actの情報を更新する」で再度登録を試みてください。"
            ),
        }

    return {**state, "eu_ai_act_text": retrieved_text}


def should_continue(state: AppState) -> str:
    return "error" if state.get("error") else "risk_assess"


def risk_assess_node(state: AppState) -> AppState:
    """Judge risk level using ONLY the RAG-retrieved EU AI Act text."""
    edited = state.get("edited") or state.get("extracted")
    if not edited:
        return {**state, "error": "評価対象の情報が見つかりません。"}

    eu_ai_act_text = state.get("eu_ai_act_text") or ""
    if not eu_ai_act_text:
        return {**state, "error": "EU AI Act条文テキストが取得されていません。"}

    info_text = (
        f"概要説明文: {edited['overview']}\n"
        f"アプリケーション利用者: {edited['users']}\n"
        f"入力情報の主体（Data Subject）: {edited['data_subjects']}\n"
        f"入力情報の情報種（情報カテゴリ）: {edited['input_data_categories']}\n"
        f"出力情報の情報種（情報カテゴリ）: {edited['output_data_categories']}\n"
        f"出力情報の利用目的: {edited['output_purposes']}"
    )

    system_prompt = RISK_SYSTEM_TEMPLATE.format(
        url=EU_AI_ACT_URL,
        eu_ai_act_text=eu_ai_act_text,
    )

    llm = make_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"以下のAgentic AIアプリケーション情報を評価してください:\n\n{info_text}"
        ),
    ]
    response = llm.invoke(messages)
    data = json.loads(_strip_fences(response.content))
    return {**state, "risk": RiskAssessment(**data)}


def error_node(state: AppState) -> AppState:
    """Terminal error pass-through node."""
    return state


# ── Graph Builders ────────────────────────────────────────────────────────────

def build_extract_graph():
    builder = StateGraph(AppState)
    builder.add_node("extract", extract_node)
    builder.set_entry_point("extract")
    builder.add_edge("extract", END)
    return builder.compile()


def build_risk_graph():
    """
    START → fetch_eu_ai_act → (error?) → risk_assess → END
                             ↘ error_node → END
    """
    builder = StateGraph(AppState)
    builder.add_node("fetch_eu_ai_act", fetch_eu_ai_act_node)
    builder.add_node("risk_assess", risk_assess_node)
    builder.add_node("error_node", error_node)

    builder.set_entry_point("fetch_eu_ai_act")
    builder.add_conditional_edges(
        "fetch_eu_ai_act",
        should_continue,
        {"risk_assess": "risk_assess", "error": "error_node"},
    )
    builder.add_edge("risk_assess", END)
    builder.add_edge("error_node", END)
    return builder.compile()


extract_graph = build_extract_graph()
risk_graph = build_risk_graph()
