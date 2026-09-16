"""Databricks-hosted foundation models, via Databricks Model Serving.

No external vendor API key needed at all. Authentication happens
automatically through the app's own Databricks service principal - the same
identity Databricks Apps already run as. A Databricks admin adds each model
as a "Serving endpoint" resource on the app (same UI flow as adding a
secret), and this module queries whichever endpoint name comes through as
an env var. Nothing to pay for beyond what the workspace already has
provisioned.

Uses the OpenAI-compatible client Databricks exposes for serving endpoints
(`w.serving_endpoints.get_open_ai_client()`) rather than the plain
ChatMessage-based query() call, since the OpenAI-compatible interface
supports multi-part content (text + images) the same way the OpenAI
provider does - useful since the served model (Claude/Gemini/GPT) is
typically vision-capable.

To offer a model here:
1. In the workspace, confirm a serving endpoint exists and is READY for it -
   check Machine Learning > Serving, or ask a Databricks admin. Databricks'
   own pay-per-token Foundation Model APIs endpoints are commonly named
   like "databricks-claude-sonnet-4-5" or "databricks-gemini-2-5-pro", but
   exact availability depends on your workspace/region.
2. On the app: App resources > + Add resource > Serving endpoint > pick it,
   permission "Can query", and give it a resource key matching one of the
   entries in MODEL_ENV_VARS below (e.g. "claude-serving-endpoint").
3. Add the matching env entry to app.yaml (see the repo's app.yaml).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from databricks.sdk import WorkspaceClient

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


def _openai_client():
    # Picks up the workspace host and this app's own auth automatically
    # when running as a Databricks App - nothing to configure here.
    w = WorkspaceClient()
    return w.serving_endpoints.get_open_ai_client()


def _endpoint_for(model: str) -> str:
    env_var = MODEL_ENV_VARS.get(model)
    endpoint_name = os.environ.get(env_var, "") if env_var else ""
    if not endpoint_name:
        raise RuntimeError(
            f"No serving endpoint is wired up for '{model}' yet. Ask a Databricks admin to "
            "add it as a Serving endpoint resource on this app (see providers/databricks_provider.py)."
        )
    return endpoint_name


def _image_blocks(docs_images: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    blocks = []
    for img in docs_images or []:
        if not img.get("data"):
            continue
        blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"},
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
    # api_key is unused here - kept so every provider module has an identical
    # call signature and app.py doesn't need to special-case this one.
    client = _openai_client()
    endpoint = _endpoint_for(model)

    text = build_plan_user_message(intake_text, docs_context) + build_image_manifest_note(
        docs_images or []
    )
    content = [{"type": "text", "text": text}] + _image_blocks(docs_images)

    response = client.chat.completions.create(
        model=endpoint,
        messages=[
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": content},
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
    client = _openai_client()
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

    response = client.chat.completions.create(
        model=endpoint,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        max_tokens=1500,
    )

    return response.choices[0].message.content
