"""LangGraph workflow for AI Risk Assessment."""
from __future__ import annotations

import json
from typing import TypedDict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END


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
    risk: Optional[RiskAssessment]
    error: Optional[str]


def make_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0)


EXTRACT_SYSTEM = """あなたは議事録を解析し、Agentic AIアプリケーションの開発・利用に関する情報を抽出する専門家です。
議事録テキストから以下の6項目を日本語で抽出・要約してください。
議事録にAgentic AIアプリケーションに関する記載がない場合は、各項目に「記載なし」と返してください。

必ずJSONのみを返してください（```json```ブロック不要、純粋なJSONのみ）:
{
  "overview": "概要説明文（このAgentic AIアプリケーションが何をするものか）",
  "users": "アプリケーション利用者（操作と出力情報の利用者）",
  "data_subjects": "入力情報の主体（Data Subject）",
  "input_data_categories": "入力情報の情報種（情報カテゴリ）",
  "output_data_categories": "出力情報の情報種（情報カテゴリ）",
  "output_purposes": "出力情報の利用目的"
}"""

RISK_SYSTEM = """あなたはEU AI Act（Regulation (EU) 2024/1689）の専門家です。
以下のAgentic AIアプリケーション情報をもとに、EU AI Actに基づくリスクレベルを判定してください。

判定基準:
- 第5条（Article 5）: 禁止される人工知能の実践
- 第6条（Article 6）: 高リスクAIシステムの分類規則（これを主な判定根拠とする）
- 第50条（Article 50）: 特定のAIシステムに対する透明性義務

リスクレベルは以下のいずれかで判定:
1. 「禁止（Prohibited）」: 第5条により禁止される実践に該当
2. 「高リスク（High-Risk）」: 第6条により高リスクAIシステムに分類
3. 「透明性義務あり（Transparency Obligation）」: 第50条の透明性義務のみが適用
4. 「限定リスク（Limited Risk）」: 上記に該当しないが特定の義務あり
5. 「最小リスク（Minimal Risk）」: 規制上の義務がほとんどない

必ずJSONのみを返してください（```json```ブロック不要、純粋なJSONのみ）:
{
  "risk_level": "リスクレベル（上記1〜5のいずれか）",
  "risk_basis": "判定根拠（第6条の該当条項・附属書を明示しながら、なぜそのリスクレベルと判定したかを詳細に説明）"
}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        else:
            text = parts[-1]
    return text.strip()


def extract_node(state: AppState) -> AppState:
    llm = make_llm()
    messages = [
        SystemMessage(content=EXTRACT_SYSTEM),
        HumanMessage(content=f"以下の議事録テキストを解析してください:\n\n{state['minutes_text']}"),
    ]
    response = llm.invoke(messages)
    data = json.loads(_strip_fences(response.content))
    return {**state, "extracted": ExtractedInfo(**data)}


def risk_assess_node(state: AppState) -> AppState:
    edited = state.get("edited") or state.get("extracted")
    if not edited:
        return {**state, "error": "編集済み情報が見つかりません"}

    info_text = f"""概要説明文: {edited['overview']}
アプリケーション利用者: {edited['users']}
入力情報の主体（Data Subject）: {edited['data_subjects']}
入力情報の情報種（情報カテゴリ）: {edited['input_data_categories']}
出力情報の情報種（情報カテゴリ）: {edited['output_data_categories']}
出力情報の利用目的: {edited['output_purposes']}"""

    llm = make_llm()
    messages = [
        SystemMessage(content=RISK_SYSTEM),
        HumanMessage(content=f"以下のAgentic AIアプリケーション情報を評価してください:\n\n{info_text}"),
    ]
    response = llm.invoke(messages)
    data = json.loads(_strip_fences(response.content))
    return {**state, "risk": RiskAssessment(**data)}


def build_extract_graph():
    builder = StateGraph(AppState)
    builder.add_node("extract", extract_node)
    builder.set_entry_point("extract")
    builder.add_edge("extract", END)
    return builder.compile()


def build_risk_graph():
    builder = StateGraph(AppState)
    builder.add_node("risk_assess", risk_assess_node)
    builder.set_entry_point("risk_assess")
    builder.add_edge("risk_assess", END)
    return builder.compile()


extract_graph = build_extract_graph()
risk_graph = build_risk_graph()
