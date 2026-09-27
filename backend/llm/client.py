"""Provider-agnostic LLM wrapper: Gemini, Groq, Ollama or Anthropic.

Person 1 (Lead Developer + DevOps) owns this file.

Every LLM call in this system is optional, so this wrapper:
  * never raises into the request path - it returns None on any failure,
  * enforces a hard timeout so the <30s product requirement holds,
  * extracts JSON defensively, because models wrap JSON in prose and fences.

`LLM_PROVIDER` selects the provider; `LLM_MODE=off` makes the whole system run
with zero network calls, which is the safest possible configuration on demo day.

Why Gemini is the default (see docs/ARCHITECTURE_NOTES.md):
  * free tier with no credit card (500 requests/day on the flash model),
  * hosted API, so it works from Render like it works locally,
  * strongest Swahili of the free options - the app is bilingual by design.
Groq is a fast fallback; Ollama is for fully offline local demos only (a local
Ollama server cannot be reached from a Render deployment).

The request builders are pure functions (`build_*_request`, `parse_*`) so the
transport can be unit-tested without network access.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from config import Settings, get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class LLMUnavailable(RuntimeError):
    """Raised only when LLM_MODE=on demands a model and none can be reached."""


# Last provider failure, kept so a deployed service can be diagnosed from its own
# API instead of from server logs. A misconfigured key otherwise looks like
# success: the provider is reported as "enabled" while every call falls back to
# the deterministic engine.
_LAST_ERROR: dict[str, Any] | None = None


def _record_error(provider: str, message: str) -> None:
    global _LAST_ERROR
    _LAST_ERROR = {
        "provider": provider,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message": message,
    }


def _record_success(provider: str) -> None:
    global _LAST_ERROR
    _LAST_ERROR = None


def last_error() -> dict[str, Any] | None:
    """The most recent provider failure, or None after a successful call."""
    return _LAST_ERROR


def probe_llm() -> dict[str, Any]:
    """Perform one small live call and report exactly what happened.

    Used by `GET /api/admin/llm-check` and `python check_llm.py` so a bad key or
    an unavailable model can be diagnosed from the deployed service itself.
    Never raises.
    """
    settings = get_settings()
    result: dict[str, Any] = {
        "provider": settings.provider,
        "model": settings.effective_model,
        "mode": settings.llm_mode,
        "configured": settings.llm_available,
        "reason": settings._llm_reason(),
        "ok": False,
        "error": None,
        "sample": None,
    }
    if not settings.llm_available:
        result["error"] = "No LLM is configured for this deployment (see 'reason')."
        return result

    before = _LAST_ERROR
    raw = call_llm(
        "You are a test probe. Reply with exactly the word OK.",
        "Reply with exactly the word OK.",
        max_tokens=16,
        temperature=0.0,
    )
    result["ok"] = raw is not None
    result["sample"] = (raw or "")[:200]
    result["error"] = None if raw is not None else (_LAST_ERROR or before or {}).get("message")
    result["last_error"] = _LAST_ERROR
    return result


def extract_json(text: str) -> dict[str, Any] | None:
    """Pull a JSON object out of a model response.

    Handles bare JSON, fenced JSON, and JSON embedded in surrounding prose.
    """
    if not text:
        return None

    candidates: list[str] = []
    stripped = text.strip()
    candidates.append(stripped)
    candidates.extend(match.group(1).strip() for match in _JSON_FENCE_RE.finditer(text))

    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(stripped[first_brace : last_brace + 1])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


# ---------------------------------------------------------------------------
# Gemini (Google AI Studio)
# ---------------------------------------------------------------------------
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def build_gemini_request(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """Pure request builder, testable without a key or network."""
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            # Force a bare JSON object back - no prose, no markdown fences.
            "responseMimeType": "application/json",
        },
    }
    if system_prompt:
        body["system_instruction"] = {"parts": [{"text": system_prompt}]}
    return {
        "url": GEMINI_ENDPOINT.format(model=settings.effective_model),
        "headers": {"x-goog-api-key": settings.gemini_api_key},
        "body": body,
    }


def parse_gemini_response(payload: Any) -> str | None:
    """Extract the first text part from a generateContent response."""
    try:
        parts = payload["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return None
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "\n".join(texts).strip() or None


# ---------------------------------------------------------------------------
# Groq (OpenAI-compatible chat completions)
# ---------------------------------------------------------------------------
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def build_groq_request(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """Pure request builder, testable without a key or network."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    body: dict[str, Any] = {
        "model": settings.effective_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    return {
        "url": GROQ_ENDPOINT,
        "headers": {"Authorization": f"Bearer {settings.groq_api_key}"},
        "body": body,
    }


def parse_groq_response(payload: Any) -> str | None:
    """Extract the assistant message from a chat.completion response."""
    try:
        return (payload["choices"][0]["message"]["content"] or "").strip() or None
    except (KeyError, IndexError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Ollama (local OpenAI-compatible API)
# ---------------------------------------------------------------------------


def build_ollama_request(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """Pure request builder for the local Ollama chat API."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return {
        "url": f"{settings.ollama_base_url}/api/chat",
        "headers": {},
        "body": {
            "model": settings.effective_model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
    }


def parse_ollama_response(payload: Any) -> str | None:
    """Extract the assistant message from an Ollama chat response."""
    if not isinstance(payload, dict):
        return None
    return (payload.get("message") or {}).get("content") or None


# ---------------------------------------------------------------------------
# Anthropic (Claude) - the original provider, kept for flexibility
# ---------------------------------------------------------------------------


def _call_anthropic(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str | None:
    try:
        import anthropic
    except ImportError:
        logger.warning("The 'anthropic' package is not installed - Claude calls disabled.")
        return None

    try:
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=float(settings.llm_timeout_seconds),
            max_retries=settings.llm_max_retries,
        )
        response = client.messages.create(
            model=settings.effective_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc

    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip() or None


# ---------------------------------------------------------------------------
# Generic dispatch
# ---------------------------------------------------------------------------
_REST_PROVIDERS = {
    "gemini": (build_gemini_request, parse_gemini_response),
    "groq": (build_groq_request, parse_groq_response),
    "ollama": (build_ollama_request, parse_ollama_response),
}


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 700,
    temperature: float = 0.0,
) -> str | None:
    """Return the provider's text response, or None if unavailable.

    Never raises unless LLM_MODE=on was explicitly requested.
    """
    settings = get_settings()
    if not settings.llm_available:
        logger.debug("LLM skipped: %s", settings._llm_reason())
        return None

    provider = settings.provider
    try:
        if provider == "anthropic":
            text = _call_anthropic(settings, system_prompt, user_prompt, max_tokens, temperature)
        elif provider in _REST_PROVIDERS:
            build, parse = _REST_PROVIDERS[provider]
            spec = build(settings, system_prompt, user_prompt, max_tokens, temperature)
            response = httpx.post(
                spec["url"],
                headers=spec["headers"],
                json=spec["body"],
                timeout=float(settings.llm_timeout_seconds),
            )
            if response.status_code >= 400:
                # The provider's own body is the useful part: it says things like
                # "API key not valid" or "model not found", which is exactly what
                # you need to fix a bad key on a deployed service.
                raise RuntimeError(_describe_http_error(response))
            text = parse(response.json())
            if text is None:
                raise RuntimeError(f"provider returned no text (HTTP {response.status_code})")
        else:
            raise RuntimeError(f"unsupported provider {provider!r}")

        _record_success(provider)
        return text
    except Exception as exc:
        message = f"{provider} call failed ({type(exc).__name__}): {exc}"
        _record_error(provider, message)
        if settings.llm_mode == "on":
            raise LLMUnavailable(message) from exc
        logger.warning("LLM call failed, using deterministic fallback. %s", message)
        return None


def _describe_http_error(response: Any) -> str:
    """Readable one-line reason from a failed provider response."""
    detail = ""
    try:
        detail = response.text[:400]
    except Exception:  # pragma: no cover - defensive
        detail = ""
    return f"HTTP {response.status_code} from {response.url}: {detail}".strip()


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 700,
) -> dict[str, Any] | None:
    """Call the configured provider and parse a JSON object from the reply."""
    raw = call_llm(system_prompt, user_prompt, max_tokens=max_tokens, temperature=0.0)
    if raw is None:
        return None
    parsed = extract_json(raw)
    if parsed is None:
        logger.warning("The LLM returned text that contained no JSON object.")
    return parsed


def llm_status() -> dict[str, Any]:
    """Report LLM configuration for /health without leaking secrets.

    `enabled` means "configured and will be attempted" - not "working". Check
    `last_error` (or call the probe) to see whether calls are actually
    succeeding, because a bad key still reports enabled=true.
    """
    settings = get_settings()
    return {
        "enabled": settings.llm_available,
        "mode": settings.llm_mode,
        "provider": settings.provider,
        "model": settings.effective_model if settings.llm_available else None,
        "reason": settings._llm_reason(),
        "last_error": _LAST_ERROR,
        "working": settings.llm_available and _LAST_ERROR is None,
    }
