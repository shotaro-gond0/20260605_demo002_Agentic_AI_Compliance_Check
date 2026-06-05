"""FAISS vector store for the EU AI Act document.

Lifecycle:
  Module import   — tries to load a previously saved index from FAISS_INDEX_DIR.
                    If found, is_ready() returns True immediately without any
                    network access or re-embedding.

  build_from_url() — called from the Gradio "更新" button handler.
                     Fetches the PDF, splits into chunks, embeds, saves the
                     index to disk, and stores it in the module-level singleton.
                     Calling again clears and rebuilds from scratch.

  retrieve(queries) — called by the LangGraph fetch_eu_ai_act_node.
                      Runs multiple similarity searches and returns
                      deduplicated chunks as a single string.

  is_ready()        — returns True once the index has been built or loaded.
  was_loaded_from_disk() — returns True if the index was auto-loaded at import.
"""
from __future__ import annotations

import io
import os
from typing import Optional

import httpx
from pypdf import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

EU_AI_ACT_URL = (
    "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689"
)

FAISS_INDEX_DIR = "/tmp/eu_ai_act_faiss"

_vectorstore: Optional[FAISS] = None
_loaded_from_disk: bool = False


# ── Disk helpers ───────────────────────────────────────────────────────────────

def _save_to_disk(store: FAISS) -> None:
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    store.save_local(FAISS_INDEX_DIR)


def _load_from_disk() -> Optional[FAISS]:
    index_file = os.path.join(FAISS_INDEX_DIR, "index.faiss")
    if not os.path.exists(index_file):
        return None
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        return FAISS.load_local(
            FAISS_INDEX_DIR,
            embeddings,
            allow_dangerous_deserialization=True,
        )
    except Exception:
        return None


# ── Auto-load at import time ───────────────────────────────────────────────────

def _try_auto_load() -> None:
    global _vectorstore, _loaded_from_disk
    store = _load_from_disk()
    if store is not None:
        _vectorstore = store
        _loaded_from_disk = True


_try_auto_load()


# ── PDF helpers ────────────────────────────────────────────────────────────────

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

def build_from_file(file_path: str) -> tuple[int, str | None]:
    """Build FAISS index from a local PDF file path.

    Returns:
        (chunk_count, None)  on success
        (0, error_message)   on failure
    """
    global _vectorstore, _loaded_from_disk

    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        return 0, f"ファイルの読み込みに失敗しました: {e}"

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
    store = FAISS.from_documents(docs, embeddings)

    _save_to_disk(store)
    _vectorstore = store
    _loaded_from_disk = False

    return len(docs), None


def build_from_url() -> tuple[int, str | None]:
    """Fetch EU AI Act PDF, (re)build the FAISS index, and save it to disk.

    Returns:
        (chunk_count, None)  on success
        (0, error_message)   on failure
    """
    global _vectorstore, _loaded_from_disk

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
    store = FAISS.from_documents(docs, embeddings)

    _save_to_disk(store)
    _vectorstore = store
    _loaded_from_disk = False

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
    """True if the vector store has been built or loaded from disk."""
    return _vectorstore is not None


def was_loaded_from_disk() -> bool:
    """True if the vector store was auto-loaded from a saved index at startup."""
    return _loaded_from_disk
