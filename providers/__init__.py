"""Registry of available AI providers.

Add a new vendor by writing a module with the same generate_plan/coach_step
interface and adding it to PROVIDERS below - nothing else in the app needs
to change.
"""
from __future__ import annotations

from . import anthropic_provider, google_provider, openai_provider

PROVIDERS = {
    anthropic_provider.DISPLAY_NAME: anthropic_provider,
    google_provider.DISPLAY_NAME: google_provider,
    openai_provider.DISPLAY_NAME: openai_provider,
}
