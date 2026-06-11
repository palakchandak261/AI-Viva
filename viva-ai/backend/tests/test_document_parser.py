"""Unit tests for document_parser service (no LLM calls)."""
import pytest
from app.services.document_parser import _detect_language, build_extracted_content


def test_detect_language():
    assert _detect_language(".py") == "Python"
    assert _detect_language(".js") == "JavaScript"
    assert _detect_language(".ts") == "TypeScript"
    assert _detect_language(".xyz") == "Unknown"


def test_build_extracted_content_no_files():
    content = build_extracted_content()
    assert content["report"] == ""
    assert content["slides"] == []
    assert content["code_files"] == []
    assert content["summary_text"] == ""
