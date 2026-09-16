"""Google (Gemini) implementation of the provider interface.

Every provider module exposes the same two functions - generate_plan and
coach_step - with the same signature, so app.py can call whichever one the
person picked without caring which vendor it is.

Gemini uses "model" instead of "assistant" as the role name for prior
responses, so chat history gets translated before each call.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from .prompts import (
    PLAN_SYSTEM_PROMPT,
    STEP_COACH_SYSTEM_TEMPLATE,
    build_image_manifest_note,
    build_plan_user_message,
    extract_json,
)

DISPLAY_NAME = "Google (Gemini)"
# Only free-tier models are listed - Gemini's Pro models require billing to
# be enabled, so they're deliberately left out here. Google no longer
# publishes exact free-tier rate limits; if these models change tier, check
# aistudio.google.com or ai.google.dev/gemini-api/docs/rate-limits.
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
KEY_ENV_VAR = "GOOGLE_API_KEY"
KEY_HELP = "Get a key at aistudio.google.com"
SUPPORTS_VISION = True


def _image_parts(docs_images: Optional[List[Dict[str, Any]]]) -> List[Any]:
    parts = []
    for img in docs_images or []:
        if not img.get("data"):
            continue
        parts.append(
            types.Part.from_bytes(
                data=base64.b64decode(img["data"]), mime_type=img["mime_type"]
            )
        )
    return parts


def _to_gemini_contents(chat_history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    contents = []
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    return contents


def generate_plan(
    api_key: str,
    model: str,
    intake_text: str,
    docs_context: str,
    docs_images: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    client = genai.Client(api_key=api_key)

    text = build_plan_user_message(intake_text, docs_context) + build_image_manifest_note(
        docs_images or []
    )
    contents = [text] + _image_parts(docs_images)

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=PLAN_SYSTEM_PROMPT,
            max_output_tokens=64000,
        ),
    )

    return extract_json(response.text)


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
    client = genai.Client(api_key=api_key)

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

    contents = _to_gemini_contents(chat_history)
    image_parts = _image_parts(docs_images)
    if image_parts and contents and contents[0]["role"] == "user":
        contents[0]["parts"] = contents[0]["parts"] + [
            {"inline_data": {"mime_type": p.inline_data.mime_type, "data": p.inline_data.data}}
            for p in image_parts
        ]

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=16000,
        ),
    )

    return response.text
