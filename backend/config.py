"""Configuration, loaded from the environment with safe defaults.

Person 1 (Lead Developer + DevOps) owns this file.

LLM providers
-------------
The LLM layer is provider-agnostic. `LLM_PROVIDER` selects one of:

    gemini     Google AI Studio - recommended default: free tier (500 req/day,
               no credit card), hosted API (works from Render), strongest
               Swahili among the free options, native JSON output mode.
    groq       Hosted Llama inference - very fast and free, but tighter rate
               limits and weaker Swahili. Good as a fallback provider.
    ollama     Local open models - no API key, works fully offline. Only usable
               when the backend runs on the same machine as Ollama, so it
               cannot power a Render deployment. Good for the recorded demo.
    anthropic  Claude - the original provider; kept for flexibility.
    none       No LLM calls, ever (same effect as LLM_MODE=off).

Triage decisions never depend on the LLM (see triage/engine.py): the provider
only structures symptoms and phrases the care advice. Switching providers
cannot change a RED/YELLOW/GREEN decision.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# This file lives at backend/config.py, so `.parent` is the backend directory
# (which holds data/). Using parents[1] here pointed one level too high - at the
# repository root - which made /api/status report `data_dir_exists: false` and
# left the loader's fallback path doing the real work. Found by inspecting the
# live Render deployment.
BACKEND_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"

VALID_PROVIDERS = ("gemini", "groq", "ollama", "anthropic", "none")

# Default model per provider, used when LLM_MODEL is not set. Verified against
# current provider documentation in September 2026; override freely.
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash-preview",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "llama3.2",
    "anthropic": "claude-haiku-4-5-20251001",
    "none": "",
}


def _load_dotenv() -> None:
    """Best-effort .env loading that never hard-fails.

    python-dotenv is a declared dependency, but the app must still start if a
    deployment platform injects real environment variables and the package is
    missing. Never let configuration loading become a demo failure.
    """
    candidates = [BACKEND_ROOT.parent / ".env", BACKEND_ROOT / ".env"]
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)


_load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the MediTriage backend."""

    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    # ---- LLM provider selection ------------------------------------------------
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini").strip().lower())
    # LLM_MODEL overrides the per-provider default. CLAUDE_MODEL is accepted for
    # backwards compatibility with the first build.
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", os.getenv("CLAUDE_MODEL", "")).strip()
    )
    llm_mode: str = field(default_factory=lambda: os.getenv("LLM_MODE", "auto").strip().lower())
    llm_timeout_seconds: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", 20))
    llm_max_retries: int = field(default_factory=lambda: _env_int("LLM_MAX_RETRIES", 1))

    # ---- Provider credentials --------------------------------------------------
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "").strip())
    # Ollama needs no key; it needs a reachable local server.
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
    )

    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("MEDITRIAGE_DATA_DIR", str(DEFAULT_DATA_DIR)))
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        )
    )

    # ---- Derived helpers -------------------------------------------------------

    @property
    def provider(self) -> str:
        return self.llm_provider if self.llm_provider in VALID_PROVIDERS else "none"

    @property
    def effective_model(self) -> str:
        """The model ID that will be used, or '' when no LLM is configured."""
        return self.llm_model or PROVIDER_DEFAULT_MODELS.get(self.provider, "")

    def _provider_key_present(self) -> bool:
        if self.provider == "gemini":
            return bool(self.gemini_api_key)
        if self.provider == "groq":
            return bool(self.groq_api_key)
        if self.provider == "ollama":
            return True  # no key; reachability is checked at call time
        if self.provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False

    @property
    def llm_available(self) -> bool:
        """True when an LLM call will actually be attempted."""
        if self.llm_mode == "off":
            return False
        if self.provider == "none":
            # `none` means "no LLM calls, ever" - LLM_MODE=on cannot override
            # it, otherwise every request attempts a call that is guaranteed
            # to raise, and the whole pipeline degrades to the fail-safe path.
            return False
        if self.llm_mode == "on":
            return True
        return self._provider_key_present()

    def describe(self) -> dict:
        """Non-secret summary, safe to expose on /health."""
        return {
            "environment": self.environment,
            "llm_mode": self.llm_mode,
            "llm_enabled": self.llm_available,
            "llm_reason": self._llm_reason(),
            "llm_provider": self.provider,
            "llm_model": self.effective_model if self.llm_available else None,
            "api_key_present": self._provider_key_present(),
            "data_dir": str(self.data_dir),
            "data_dir_exists": self.data_dir.exists(),
            "cors_origins": list(self.cors_origins),
        }

    def _llm_reason(self) -> str:
        if self.llm_mode == "off":
            return "LLM_MODE=off - deterministic rule engine only"
        if self.provider == "none":
            if self.llm_provider == "none":
                return "LLM_PROVIDER=none - deterministic offline mode"
            return f"LLM_PROVIDER={self.llm_provider!r} is not a supported provider - deterministic offline mode"
        if not self._provider_key_present():
            key_name = {
                "gemini": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
            }.get(self.provider)
            if self.llm_mode == "on":
                return f"LLM_MODE=on but {key_name} is not set - LLM calls will fail"
            return f"{key_name} not set - running in deterministic offline mode"
        return f"{self.provider} enabled ({self.effective_model})"


def get_settings() -> Settings:
    """Return settings, re-read from the environment on every call.

    Re-reading (instead of caching) keeps tests and local .env edits predictable.
    """
    return Settings()
