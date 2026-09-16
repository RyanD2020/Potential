"""Registry of AI providers shown in the app.

Only genuinely free-to-run options are registered here:
  - Databricks (no key needed): free in the sense that it uses whatever
    the workspace already has provisioned - no new vendor account or bill.
  - Google (Gemini): its free tier needs no billing account at all.

Anthropic and OpenAI have no free tier as of this writing (both require a
paid account), so their modules stay in this folder - fully working,
same interface - but are NOT registered below. If real, funded keys ever
become available for either, re-enable them by importing the module and
adding it to PROVIDERS; nothing else in the app needs to change.
"""
from __future__ import annotations

from . import databricks_provider, google_provider

PROVIDERS = {
    databricks_provider.DISPLAY_NAME: databricks_provider,
    google_provider.DISPLAY_NAME: google_provider,
}

# Kept available but not user-facing until there's a funded key for them:
# from . import anthropic_provider, openai_provider
