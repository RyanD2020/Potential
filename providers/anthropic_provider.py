"""Anthropic (Claude) implementation of the provider interface.

Every provider module exposes the same two functions - generate_plan and
coach_step - with the same signature, so app.py can call whichever one the
person picked without caring which vendor it is.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import anthropic

from .prompts import (
    PLAN_SYSTEM_PROMPT,
    STEP_COACH_SYSTEM_TEMPLATE,
    build_image_manifest_note,
    build_plan_user_message,
    extract_json,
)

DISPLAY_NAME = "Anthropic (Claude)"
MODELS = ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"]
KEY_ENV_VAR = "ANTHROPIC_API_KEY"
KEY_HELP = "Get a key at console.anthropic.com"
SUPPORTS_VISION = True


def _image_blocks(docs_images: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    blocks = []
    for img in docs_images or []:
        if not img.get("data"):
            continue
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["mime_type"],
                    "data": img["data"],
                },
            }
        )
    return blocks


def generate_plan(
    api_key: str,
    model: str,
    intake_text: str,
    docs_context: str,
    docs_images: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    client = anthropic.Anthropic(api_key=api_key)

    text = build_plan_user_message(intake_text, docs_context) + build_image_manifest_note(
        docs_images or []
    )
    content = [{"type": "text", "text": text}] + _image_blocks(docs_images)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=PLAN_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")
    return extract_json(raw_text)


def coach_step(
    api_key: str,
    model: str,
    project_title: str,
    project_summary: str,
    phase_title: str,
    phase_goal: str,
    step_title: str,
    step_description: str,
    why_it_matters: str,
    docs_context: str,
    chat_history: List[Dict[str, str]],
    docs_images: Optional[List[Dict[str, Any]]] = None,
) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = STEP_COACH_SYSTEM_TEMPLATE.format(
        project_title=project_title,
        project_summary=project_summary,
        phase_title=phase_title,
        phase_goal=phase_goal,
        step_title=step_title,
        step_description=step_description,
        why_it_matters=why_it_matters,
        docs_context=docs_context or "(none provided)",
    )

    # Attach images to the first user turn only, so they aren't re-sent on
    # every message in the conversation.
    messages = list(chat_history)
    image_blocks = _image_blocks(docs_images)
    if image_blocks and messages and messages[0]["role"] == "user":
        first = messages[0]
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": first["content"]}] + image_blocks,
            }
        ] + messages[1:]

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system_prompt,
        messages=messages,
    )

    return "".join(block.text for block in response.content if block.type == "text")
