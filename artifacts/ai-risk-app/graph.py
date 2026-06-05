"""LangGraph workflow for AI Risk Assessment.

Risk graph architecture:
  START → fetch_eu_ai_act → risk_assess → END

The fetch node downloads the EU AI Act PDF from EUR-Lex on every invocation
and extracts Articles 5, 6, and 50.  The risk_assess node uses *only* that
fetched text as grounding — no embedded legal knowledge.
"""
from __future__ import annotations

import io
import json
import re
from typing import TypedDict, Optional

import httpx
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

EU_AI_ACT_URL = (
    "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689"
)

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
    eu_ai_act_text: Optional[str]   # Fetched from EUR-Lex on every risk run
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


def _fetch_pdf_bytes(url: str) -> tuple[bytes, str | None]:
    """Download a URL and return (bytes, error_message)."""
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.content, None
    except httpx.HTTPStatusError as e:
        return b"", (
            f"EU AI Act PDFの取得に失敗しました（HTTP {e.response.status_code}）。\n"
            f"URL: {url}"
        )
    except Exception as e:
        return b"", (
            f"EU AI Act PDFへのアクセスに失敗しました: {e}\n"
            f"URL: {url}"
        )


def _pdf_bytes_to_text(data: bytes) -> tuple[str, str | None]:
    """Extract plain text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages)
        if not text.strip():
            return "", "PDFからテキストを抽出できませんでした。"
        return text, None
    except Exception as e:
        return "", f"PDFの解析に失敗しました: {e}"


def _extract_articles(full_text: str) -> str:
    """Extract Articles 5, 6, and 50 from the EU AI Act full text."""
    parts = []
    for num in ("5", "6", "50"):
        # Match "Article <num>" up to the next "Article <digits>" or end
        pattern = (
            rf"(Article\s+{num}\b[\s\S]*?)"
            rf"(?=\nArticle\s+\d+\b|\Z)"
        )
        matches = re.findall(pattern, full_text)
        if matches:
            # Keep the longest match and cap at 5000 chars
            snippet = max(matches, key=len)[:5000]
            parts.append(f"=== Article {num} ===\n{snippet}")

    return "\n\n".join(parts) if parts else ""


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

以下の【EU AI Act 条文テキスト】は、公式PDFから直接抽出したものです。
このテキストの内容だけを根拠として、提供されたAgentic AIアプリケーションの
リスクレベルを判定してください。

制約:
- 条文テキスト以外の知識・推測を使用しないこと
- 条文テキストに判定根拠が見当たらない場合は、その旨を明記すること
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

【EU AI Act 条文テキスト（Article 5 / 6 / 50 抜粋）】
{eu_ai_act_text}
"""

# ── Graph Nodes ───────────────────────────────────────────────────────────────

def extract_node(state: AppState) -> AppState:
    """Extract Agentic AI info from meeting minutes."""
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
    """Sub-agent: fetch EU AI Act PDF from EUR-Lex and extract Articles 5/6/50."""
    pdf_bytes, err = _fetch_pdf_bytes(EU_AI_ACT_URL)
    if err:
        return {**state, "error": err}

    full_text, err = _pdf_bytes_to_text(pdf_bytes)
    if err:
        return {**state, "error": err}

    articles = _extract_articles(full_text)
    if not articles:
        # Fallback: keep the first 15000 chars if article extraction fails
        articles = full_text[:15000]
        if not articles.strip():
            return {
                **state,
                "error": (
                    "EU AI ActのPDFからArticle 5・6・50の条文を見つけられませんでした。"
                ),
            }

    return {**state, "eu_ai_act_text": articles}


def should_continue(state: AppState) -> str:
    """Route: skip risk_assess if an error occurred in fetch."""
    return "error" if state.get("error") else "risk_assess"


def risk_assess_node(state: AppState) -> AppState:
    """Assess EU AI Act risk using only the fetched article text."""
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

    system_prompt = RISK_SYSTEM_TEMPLATE.format(eu_ai_act_text=eu_ai_act_text)

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
    """Terminal error node — passes state through unchanged."""
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
    Graph:
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
        {
            "risk_assess": "risk_assess",
            "error": "error_node",
        },
    )
    builder.add_edge("risk_assess", END)
    builder.add_edge("error_node", END)
    return builder.compile()


extract_graph = build_extract_graph()
risk_graph = build_risk_graph()
