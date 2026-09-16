"""OpenAI (GPT) implementation of the provider interface, via the Responses API.

Every provider module exposes the same two functions - generate_plan and
coach_step - with the same signature, so app.py can call whichever one the
person picked without caring which vendor it is.
"""
from __future__ import annotations

from typing import Any, Dict, List

from openai import OpenAI

from .prompts import (
    PLAN_SYSTEM_PROMPT,
    STEP_COACH_SYSTEM_TEMPLATE,
    build_plan_user_message,
    extract_json,
)

DISPLAY_NAME = "OpenAI (GPT)"
MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
KEY_ENV_VAR = "OPENAI_API_KEY"
KEY_HELP = "Get a key at platform.openai.com"


def generate_plan(api_key: str, model: str, intake_text: str, docs_context: str) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model,
        instructions=PLAN_SYSTEM_PROMPT,
        input=[{"role": "user", "content": build_plan_user_message(intake_text, docs_context)}],
        max_output_tokens=4000,
    )

    return extract_json(response.output_text)


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
) -> str:
    client = OpenAI(api_key=api_key)

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

    # The Responses API accepts the same {"role": "user"/"assistant", "content": ...}
    # shape we already keep in session state, so chat_history can be passed straight through.
    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=chat_history,
        max_output_tokens=1500,
    )

    return response.output_text
