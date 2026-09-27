"""Shared pytest fixtures.

Every test runs with the LLM forced off, so the suite is deterministic and
never depends on a network call or an API key.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Force the deterministic path before any application module is imported.
# Every provider key is removed so a stray credential can never make the suite
# reach the network; provider tests opt back in explicitly via monkeypatch.
os.environ["LLM_MODE"] = "off"
for _key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
    os.environ.pop(_key, None)


@pytest.fixture(scope="session")
def knowledge_base():
    from knowledge.loader import load_knowledge_base

    return load_knowledge_base()


@pytest.fixture(scope="session")
def demo_cases(knowledge_base):
    return knowledge_base.test_cases


@pytest.fixture(scope="session")
def regression_cases(knowledge_base):
    return knowledge_base.regression_cases


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as test_client:
        yield test_client
