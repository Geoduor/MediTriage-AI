"""Tests for the provider-agnostic LLM layer.

No network, no API keys: the request builders are pure functions and the
transport is exercised through a mocked httpx.post. This is what makes the
provider switch (gemini -> groq -> ollama -> anthropic) safe to do on demo day.
"""
from __future__ import annotations

import pytest

from config import PROVIDER_DEFAULT_MODELS, Settings, get_settings
from llm import client as llm_client
from llm.client import (
    LLMUnavailable,
    build_gemini_request,
    build_groq_request,
    build_ollama_request,
    call_llm,
    call_llm_json,
    extract_json,
    llm_status,
    parse_gemini_response,
    parse_groq_response,
    parse_ollama_response,
)


def _settings(**overrides) -> Settings:
    settings = get_settings()
    return Settings(
        environment=settings.environment,
        log_level=settings.log_level,
        llm_provider=overrides.get("llm_provider", settings.llm_provider),
        llm_model=overrides.get("llm_model", settings.llm_model),
        llm_mode=overrides.get("llm_mode", settings.llm_mode),
        llm_timeout_seconds=overrides.get("llm_timeout_seconds", settings.llm_timeout_seconds),
        llm_max_retries=overrides.get("llm_max_retries", settings.llm_max_retries),
        gemini_api_key=overrides.get("gemini_api_key", settings.gemini_api_key),
        groq_api_key=overrides.get("groq_api_key", settings.groq_api_key),
        anthropic_api_key=overrides.get("anthropic_api_key", settings.anthropic_api_key),
        ollama_base_url=overrides.get("ollama_base_url", settings.ollama_base_url),
        data_dir=settings.data_dir,
        cors_origins=settings.cors_origins,
    )


GEMINI = _settings(llm_provider="gemini", gemini_api_key="test-gemini-key", llm_model="gemini-2.5-flash-preview")
GROQ = _settings(llm_provider="groq", groq_api_key="test-groq-key", llm_model="llama-3.3-70b-versatile")
OLLAMA = _settings(llm_provider="ollama", llm_model="llama3.2")


class TestGemini:
    def test_request_targets_model_endpoint(self):
        spec = build_gemini_request(GEMINI, "sys", "user text", 500, 0.1)
        assert spec["url"] == (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.5-flash-preview:generateContent"
        )
        assert spec["headers"] == {"x-goog-api-key": "test-gemini-key"}

    def test_request_forces_json_output(self):
        spec = build_gemini_request(GEMINI, "sys", "user text", 500, 0.1)
        config = spec["body"]["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        assert config["maxOutputTokens"] == 500
        assert config["temperature"] == 0.1

    def test_request_includes_system_instruction(self):
        spec = build_gemini_request(GEMINI, "be careful", "user text", 500, 0.0)
        assert spec["body"]["system_instruction"]["parts"][0]["text"] == "be careful"
        assert spec["body"]["contents"][0]["parts"][0]["text"] == "user text"

    def test_parse_happy_path(self):
        payload = {"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}]}
        assert parse_gemini_response(payload) == '{"a": 1}'

    def test_parse_joins_multiple_parts(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "part1"}, {"text": "part2"}]}}]}
        assert parse_gemini_response(payload) == "part1\npart2"

    def test_parse_malformed_returns_none(self):
        assert parse_gemini_response({}) is None
        assert parse_gemini_response({"candidates": []}) is None
        assert parse_gemini_response(None) is None


class TestGroq:
    def test_request_shape(self):
        spec = build_groq_request(GROQ, "sys", "user text", 400, 0.0)
        assert spec["url"] == "https://api.groq.com/openai/v1/chat/completions"
        assert spec["headers"]["Authorization"] == "Bearer test-groq-key"
        assert spec["body"]["model"] == "llama-3.3-70b-versatile"
        assert spec["body"]["response_format"] == {"type": "json_object"}
        assert spec["body"]["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "user text"},
        ]

    def test_parse_happy_path(self):
        payload = {"choices": [{"message": {"content": '{"ok": true}'}}]}
        assert parse_groq_response(payload) == '{"ok": true}'

    def test_parse_malformed_returns_none(self):
        assert parse_groq_response({}) is None


class TestOllama:
    def test_request_shape(self):
        spec = build_ollama_request(OLLAMA, "sys", "user text", 300, 0.2)
        assert spec["url"] == "http://localhost:11434/api/chat"
        assert spec["body"]["model"] == "llama3.2"
        assert spec["body"]["format"] == "json"
        assert spec["body"]["stream"] is False
        assert spec["body"]["options"]["num_predict"] == 300

    def test_parse_happy_path(self):
        payload = {"message": {"content": '{"ok": true}'}}
        assert parse_ollama_response(payload) == '{"ok": true}'

    def test_parse_malformed_returns_none(self):
        assert parse_ollama_response({}) is None


class TestDispatch:
    def test_llm_skipped_when_disabled(self, monkeypatch):
        # conftest forces LLM_MODE=off for the whole suite.
        assert call_llm("sys", "user") is None

    def test_unknown_provider_never_calls_network(self, monkeypatch):
        called = []

        def fake_post(*args, **kwargs):
            called.append(args)
            raise AssertionError("network must not be called")

        monkeypatch.setattr(llm_client.httpx, "post", fake_post)
        assert call_llm("sys", "user") is None
        assert called == []

    def test_call_llm_gemini_builds_and_parses(self, monkeypatch):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}]}

        def fake_post(url, headers, json, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr(llm_client.httpx, "post", fake_post)
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "key-123")
        monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash-preview")

        result = call_llm("sys", "user text", max_tokens=400)
        assert result == '{"a": 1}'
        assert captured["headers"]["x-goog-api-key"] == "key-123"
        assert "gemini-2.5-flash-preview" in captured["url"]
        assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"

    def test_call_llm_json_extracts_dict(self, monkeypatch):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": "```json\n{\"primary\":\"fever\"}\n```"}]}}]}

        monkeypatch.setattr(llm_client.httpx, "post", lambda *a, **k: FakeResponse())
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "key-123")

        assert call_llm_json("sys", "user") == {"primary": "fever"}

    def test_failure_returns_none_unless_mode_on(self, monkeypatch):
        def exploding_post(*args, **kwargs):
            raise ConnectionError("offline")

        monkeypatch.setattr(llm_client.httpx, "post", exploding_post)
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "key-123")
        assert call_llm("sys", "user") is None  # degrades, never raises

        monkeypatch.setenv("LLM_MODE", "on")
        with pytest.raises(LLMUnavailable):
            call_llm("sys", "user")


class TestSettingsProviderLogic:
    def test_gemini_is_the_default_provider(self):
        assert Settings().provider == "gemini"

    def test_gemini_key_enables_llm_in_auto_mode(self, monkeypatch):
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "k")
        assert get_settings().llm_available is True

    def test_missing_key_disables_llm_in_auto_mode(self, monkeypatch):
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert get_settings().llm_available is False

    def test_ollama_needs_no_key(self, monkeypatch):
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        assert get_settings().llm_available is True

    def test_invalid_provider_resolves_to_none(self, monkeypatch):
        monkeypatch.setenv("LLM_MODE", "auto")
        monkeypatch.setenv("LLM_PROVIDER", "mystery-provider")
        monkeypatch.setenv("GEMINI_API_KEY", "k")
        settings = get_settings()
        assert settings.provider == "none"
        assert settings.llm_available is False

    def test_effective_model_uses_provider_defaults(self):
        assert PROVIDER_DEFAULT_MODELS["gemini"] == "gemini-2.5-flash-preview"
        assert PROVIDER_DEFAULT_MODELS["groq"]
        assert PROVIDER_DEFAULT_MODELS["ollama"]
        assert PROVIDER_DEFAULT_MODELS["anthropic"]

    def test_llm_model_override_beats_default(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("LLM_MODEL", "gemini-2.5-pro-preview")
        assert get_settings().effective_model == "gemini-2.5-pro-preview"

    def test_llm_status_reports_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_MODE", "off")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        status = llm_status()
        assert status["provider"] == "gemini"
        assert status["enabled"] is False


class TestExtractJson:
    def test_bare_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_embedded_in_prose(self):
        assert extract_json('Here you go: {"a": 1} - hope that helps') == {"a": 1}

    def test_garbage_returns_none(self):
        assert extract_json("no json here") is None
        assert extract_json("") is None
