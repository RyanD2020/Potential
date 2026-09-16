"""Databricks-hosted foundation models, via Databricks Model Serving.

No external vendor API key needed at all. Authentication happens
automatically through the app's own Databricks service principal - the same
identity Databricks Apps already run as. A Databricks admin adds each model
as a "Serving endpoint" resource on the app (same UI flow as adding a
secret), and this module queries whichever endpoint name comes through as
an env var. Nothing to pay for beyond what the workspace already has
provisioned.

Uses the plain databricks-sdk `serving_endpoints.query()` call rather than
the OpenAI-compatible client (`get_open_ai_client()`), since that method
requires a newer databricks-sdk version than may be installed and isn't
worth the version fragility. The tradeoff: this path sends text only - it
does NOT support real vision/image input the way the Gemini provider does.
If someone uploads an image, its filename is still mentioned in the text
context, but the model won't actually see the image through this provider.

To offer a model here:
1. Check Unity Gateway > Models in the workspace (or ask a Databricks
   admin) for what's available and READY. Databricks-hosted model services
   there are queried as "system.ai.<name>" - for example
   "system.ai.claude-sonnet-5" or "system.ai.gemini-3-8-flash". (Classic,
   pre-Unity-Gateway serving endpoints are instead queried by their plain
   endpoint name, e.g. "databricks-claude-sonnet-4-5" - check which kind
   your workspace has.)
2. On the app: App resources > + Add resource > Serving endpoint > pick it,
   permission "Can query", and give it a resource key matching one of the
   entries in MODEL_ENV_VARS below (e.g. "claude-serving-endpoint").
3. Add the matching env entry to app.yaml (see the repo's app.yaml).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from .prompts import (
    PLAN_SYSTEM_PROMPT,
    STEP_COACH_SYSTEM_TEMPLATE,
    build_image_manifest_note,
    build_plan_user_message,
    extract_json,
)

DISPLAY_NAME = "Databricks (no key needed)"
KEY_ENV_VAR = None  # No API key concept for this provider.
KEY_HELP = "Runs on this app's own Databricks identity - nothing to enter."
SUPPORTS_VISION = False  # Uses serving_endpoints.query(), which is text-only.

# Friendly label -> env var holding that model's serving endpoint name.
# Add a row here for each serving endpoint an admin wires up as an app
# resource; app.yaml's `env` section is what actually populates these.
MODEL_ENV_VARS = {
    "Claude (via Databricks)": "CLAUDE_SERVING_ENDPOINT",
    "Gemini (via Databricks)": "GEMINI_SERVING_ENDPOINT",
    "GPT (via Databricks)": "GPT_SERVING_ENDPOINT",
}


def _available_models() -> List[str]:
    configured = [label for label, env_var in MODEL_ENV_VARS.items() if os.environ.get(env_var)]
    return configured or ["No models configured yet - see providers/databricks_provider.py"]


MODELS = _available_models()


def _client() -> WorkspaceClient:
    # Picks up the workspace host and this app's own auth automatically
    # when running as a Databricks App - nothing to configure here.
    return WorkspaceClient()


def _endpoint_for(model: str) -> str:
    env_var = MODEL_ENV_VARS.get(model)
    endpoint_name = os.environ.get(env_var, "") if env_var else ""
    if not endpoint_name:
        raise RuntimeError(
            f"No serving endpoint is wired up for '{model}' yet. Ask a Databricks admin to "
            "add it as a Serving endpoint resource on this app (see providers/databricks_provider.py)."
        )
    return endpoint_name


def generate_plan(
    api_key: str,
    model: str,
    intake_text: str,
    docs_context: str,
    docs_images: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    # api_key is unused here - kept so every provider module has an identical
    # call signature and app.py doesn't need to special-case this one.
    w = _client()
    endpoint = _endpoint_for(model)

    text = build_plan_user_message(intake_text, docs_context) + build_image_manifest_note(
        docs_images or []
    )

    response = w.serving_endpoints.query(
        name=endpoint,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=PLAN_SYSTEM_PROMPT),
            ChatMessage(role=ChatMessageRole.USER, content=text),
        ],
        max_tokens=4000,
    )

    return extract_json(response.choices[0].message.content)


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
    w = _client()
    endpoint = _endpoint_for(model)

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

    image_note = build_image_manifest_note(docs_images or [])

    messages = [ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt)]
    for i, msg in enumerate(chat_history):
        role = ChatMessageRole.ASSISTANT if msg["role"] == "assistant" else ChatMessageRole.USER
        content = msg["content"]
        # Mention attached image filenames alongside the first user turn only.
        if i == 0 and role == ChatMessageRole.USER:
            content += image_note
        messages.append(ChatMessage(role=role, content=content))

    response = w.serving_endpoints.query(name=endpoint, messages=messages, max_tokens=1500)
    return response.choices[0].message.content
