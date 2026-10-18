"""Every test starts from a clean environment, so the result does not depend on the machine it runs on.

Without this, a setting in your shell (capture switched on, a live model enabled, an API key) or a register
saved by using the app could change what a test sees. Tests that need a setting set it themselves.
"""
import os
import pytest

PREFIXES = ('GENAI_', 'GOVERNANCE_', 'LLM_')
NAMES = ('ENABLE_LIVE_CLASSIFICATION', 'DAILY_CLASSIFICATION_LIMIT', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY',
         'GOOGLE_API_KEY', 'XAI_API_KEY', 'GROK_API_KEY')

@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith(PREFIXES) or name in NAMES:
            monkeypatch.delenv(name)
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'home'))
