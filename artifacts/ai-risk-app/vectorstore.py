"""In-memory FAISS vector store for the EU AI Act document.

Lifecycle:
  build_from_url()  — called from the Gradio "更新" button handler.
                      Fetches the PDF, splits into chunks, embeds, and
                      stores in a module-level FAISS index.
                      Calling again clears and rebuilds from scratch.

  retrieve(queries) — called by the LangGraph fetch_eu_ai_act_node.
                      Runs multiple similarity searches and returns
                      deduplicated chunks as a single string.

  is_ready()        — returns True once the index has been built.
"""
from __future__ import annotations

import io
from typing import Optional

import httpx
from pypdf import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

EU_AI_ACT_URL = (
    "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689"
)

# Module-level singleton — rebuilt every time the user clicks "更新"
_vectorstore: Optional[FAISS] = None


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _fetch_pdf_bytes(url: str) -> tuple[bytes, str | None]:
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
        return b"", f"EU AI Act PDFへのアクセスに失敗しました: {e}\nURL: {url}"


def _pdf_bytes_to_text(data: bytes) -> tuple[str, str | None]:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages)
        if not text.strip():
            return "", "PDFからテキストを抽出できませんでした。"
        return text, None
    except Exception as e:
        return "", f"PDFの解析に失敗しました: {e}"


# ── Public API ────────────────────────────────────────────────────────────────

def build_from_url() -> tuple[int, str | None]:
    """Fetch EU AI Act PDF and (re)build the FAISS index.

    Returns:
        (chunk_count, None)  on success
        (0, error_message)   on failure
    """
    global _vectorstore

    pdf_bytes, err = _fetch_pdf_bytes(EU_AI_ACT_URL)
    if err:
        return 0, err

    full_text, err = _pdf_bytes_to_text(pdf_bytes)
    if err:
        return 0, err

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )
    docs = splitter.create_documents([full_text])
    if not docs:
        return 0, "テキストのチャンク分割に失敗しました。"

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    _vectorstore = FAISS.from_documents(docs, embeddings)

    return len(docs), None


def retrieve(queries: list[str], k_per_query: int = 6) -> str:
    """Search the vector store with multiple queries and return merged chunks.

    Duplicates are removed; order follows query priority.
    Returns empty string if the store is not ready.
    """
    if _vectorstore is None:
        return ""

    seen: set[str] = set()
    parts: list[str] = []

    for q in queries:
        results = _vectorstore.similarity_search(q, k=k_per_query)
        for doc in results:
            content = doc.page_content.strip()
            if content and content not in seen:
                seen.add(content)
                parts.append(content)

    return "\n\n---\n\n".join(parts)


def is_ready() -> bool:
    """True if the vector store has been built."""
    return _vectorstore is not None
