"""Renders a chat message's content, splitting out fenced code blocks so
they get real syntax highlighting, a built-in copy button (via st.code),
and a direct download button - instead of showing everything as flat text
the person has to manually select and copy.

This matters most for anyone working through a coding-related step without
their own coding assistant or IDE: getting a runnable file out of the chat
should be a button, not a copy-paste exercise.
"""
from __future__ import annotations

import re

import streamlit as st

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

_EXTENSIONS = {
    "python": "py",
    "py": "py",
    "javascript": "js",
    "js": "js",
    "typescript": "ts",
    "ts": "ts",
    "jsx": "jsx",
    "tsx": "tsx",
    "bash": "sh",
    "sh": "sh",
    "shell": "sh",
    "html": "html",
    "css": "css",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "sql": "sql",
    "toml": "toml",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "csharp": "cs",
    "go": "go",
    "rust": "rs",
    "r": "r",
}


def _extension_for(language: str) -> str:
    return _EXTENSIONS.get((language or "").lower(), "txt")


def contains_code(content: str) -> bool:
    """Check whether a message contains at least one fenced code block,
    without rendering it - used to decide whether to show the
    paste-error-get-a-fix action after the most recent message."""
    return bool(_CODE_BLOCK_RE.search(content or ""))


def render_message_content(content: str, key_prefix: str) -> bool:
    """Render a chat message, pulling out fenced code blocks so each one
    gets proper highlighting plus its own download button.

    key_prefix must be unique per message so download button widget keys
    don't collide across different messages/steps.

    Returns True if at least one code block was rendered - callers use
    this to decide whether to offer a "paste the error, get a fix" action
    right after this message.
    """
    pos = 0
    block_idx = 0

    for match in _CODE_BLOCK_RE.finditer(content):
        before = content[pos : match.start()]
        if before.strip():
            st.markdown(before)

        language = match.group(1) or "text"
        code = match.group(2)
        st.code(code, language=language if language != "text" else None)

        ext = _extension_for(language)
        st.download_button(
            f"⬇ Download this {language if language != 'text' else 'code'} snippet",
            data=code,
            file_name=f"snippet_{block_idx + 1}.{ext}",
            mime="text/plain",
            key=f"{key_prefix}-code-{block_idx}",
        )

        pos = match.end()
        block_idx += 1

    remainder = content[pos:]
    if remainder.strip():
        st.markdown(remainder)

    if block_idx == 0 and not content.strip():
        # Nothing matched and nothing left over - still show something
        # rather than silently rendering a blank message.
        st.markdown(content)

    return block_idx > 0
