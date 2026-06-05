"""FAISS vector store for the EU AI Act document.

Lifecycle:
  Module import    — tries to load a previously saved index from FAISS_INDEX_DIR.
                     If found, is_ready() returns True immediately without any
                     network access or re-embedding.

  build_from_web() — called from the Gradio "更新" button handler.
                     Asynchronously fetches all 113 articles from
                     artificialintelligenceact.eu, splits into chunks,
                     embeds, saves the index to disk, and stores it in the
                     module-level singleton.
                     Calling again clears and rebuilds from scratch.

  retrieve(queries) — called by the LangGraph fetch_eu_ai_act_node.
                      Runs multiple similarity searches and returns
                      deduplicated chunks as a single string.

  is_ready()        — returns True once the index has been built or loaded.
  was_loaded_from_disk() — returns True if the index was auto-loaded at import.
"""
from __future__ import annotations

import asyncio
import os
import re
from typing import Optional

import httpx
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

EU_AI_ACT_SOURCE_URL = "https://artificialintelligenceact.eu/the-act/"
_ARTICLE_BASE_URL = "https://artificialintelligenceact.eu/article/"
_ARTICLE_COUNT = 113
_FETCH_CONCURRENCY = 20

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


# ── Web scraping helpers ───────────────────────────────────────────────────────

def _extract_text_from_html(html: str) -> str:
    """Strip scripts, styles, and tags from HTML; return clean text."""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    content = body_m.group(1) if body_m else html
    text = re.sub(r'<[^>]+>', ' ', content)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def _fetch_article(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    n: int,
) -> str:
    url = f"{_ARTICLE_BASE_URL}{n}/"
    async with sem:
        try:
            r = await client.get(url, timeout=30)
            if r.status_code != 200:
                return ""
            return f"[Article {n}]\n{_extract_text_from_html(r.text)}"
        except Exception:
            return ""


async def _scrape_all_articles() -> tuple[str, str | None]:
    """Fetch all EU AI Act articles asynchronously.

    Returns:
        (full_text, None)     on success
        ("", error_message)   on failure
    """
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [_fetch_article(client, sem, n) for n in range(1, _ARTICLE_COUNT + 1)]
        results = await asyncio.gather(*tasks)

    texts = [t for t in results if t.strip()]
    if not texts:
        return "", (
            "EU AI Act の条文テキストを取得できませんでした。\n"
            f"取得元: {EU_AI_ACT_SOURCE_URL}"
        )
    return "\n\n".join(texts), None


# ── Public API ────────────────────────────────────────────────────────────────

def build_from_web() -> tuple[int, str | None]:
    """Fetch all EU AI Act articles from the web and (re)build the FAISS index.

    Returns:
        (chunk_count, None)  on success
        (0, error_message)   on failure
    """
    global _vectorstore, _loaded_from_disk

    try:
        full_text, err = asyncio.run(_scrape_all_articles())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            full_text, err = loop.run_until_complete(_scrape_all_articles())
        finally:
            loop.close()

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
