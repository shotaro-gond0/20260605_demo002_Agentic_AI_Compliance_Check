"""Unit tests for pdf_report.py — font loading and PDF generation."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdf_report import _ensure_fonts, generate_pdf


def test_ensure_fonts_returns_true():
    """Bundled Noto Sans JP fonts must be present — no network access required."""
    assert _ensure_fonts() is True, (
        "NotoSansJP-Regular.ttf / NotoSansJP-Bold.ttf が "
        "artifacts/ai-risk-app/fonts/ に存在しません"
    )


def test_generate_pdf_returns_valid_pdf_binary(tmp_path):
    """generate_pdf() must produce a file whose content starts with the PDF header."""
    path = generate_pdf(
        risk_level="高リスク（High-Risk）",
        risk_basis="EU AI Act 第6条第2項に基づき高リスクと判定。",
        overview="採用選考を支援するAIシステム。",
        users="人事担当者",
        data_subjects="求職者",
        input_cats="氏名、学歴、職歴",
        output_cats="スコア、採否推薦",
        purposes="採用可否の補助判断",
        eu_ai_act_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
    )
    try:
        assert os.path.exists(path), f"PDFファイルが生成されていません: {path}"
        with open(path, "rb") as f:
            header = f.read(4)
        assert header == b"%PDF", (
            f"有効なPDFヘッダー（%PDF）が見つかりません。先頭4バイト: {header!r}"
        )
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_generate_pdf_file_size_is_reasonable(tmp_path):
    """Generated PDF should be at least 10 KB (confirms content was written)."""
    path = generate_pdf(
        risk_level="透明性（Transparency）",
        risk_basis="EU AI Act 第50条に基づき透明性義務が適用される。",
        overview="チャットボットによる顧客対応システム。",
        users="一般消費者",
        data_subjects="顧客",
        input_cats="テキスト入力",
        output_cats="テキスト応答",
        purposes="カスタマーサポート",
        eu_ai_act_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
    )
    try:
        size = os.path.getsize(path)
        assert size >= 10_000, f"PDFサイズが小さすぎます ({size} bytes)。生成に失敗している可能性があります。"
    finally:
        if os.path.exists(path):
            os.unlink(path)
