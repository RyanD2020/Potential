"""Utilities for extracting text from uploaded supporting documents.

Keeps document parsing separate from the Streamlit UI and the Claude calls,
so each file has one clear job.
"""
from __future__ import annotations

import io
from typing import List

MAX_CHARS_PER_DOC = 8000  # keeps prompts a reasonable size even with several docs


def extract_text_from_file(uploaded_file) -> str:
    """Extract plain text from a Streamlit UploadedFile.

    Supports .txt, .md, .pdf, and .docx. Returns a readable error message
    (instead of raising) for anything else, so a bad upload never crashes
    the app.
    """
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    try:
        if name.endswith(".txt") or name.endswith(".md"):
            return data.decode("utf-8", errors="ignore")

        if name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)

        if name.endswith(".docx"):
            import docx

            document = docx.Document(io.BytesIO(data))
            paragraphs = [p.text for p in document.paragraphs]
            return "\n".join(paragraphs)

        return (
            f"[Unsupported file type for '{uploaded_file.name}' - "
            "only .txt, .md, .pdf, .docx are read.]"
        )

    except Exception as exc:  # noqa: BLE001 - surface any parser error to the user
        return f"[Could not read '{uploaded_file.name}': {exc}]"


def build_supporting_docs_context(uploaded_files: List) -> str:
    """Turn a list of uploaded files into one context string for Claude.

    Each document is truncated to MAX_CHARS_PER_DOC so a handful of large
    uploads don't blow out the prompt.
    """
    if not uploaded_files:
        return ""

    sections = []
    for f in uploaded_files:
        text = extract_text_from_file(f)
        if len(text) > MAX_CHARS_PER_DOC:
            text = text[:MAX_CHARS_PER_DOC] + "\n...[truncated]..."
        sections.append(f"--- Document: {f.name} ---\n{text}")

    return "\n\n".join(sections)
