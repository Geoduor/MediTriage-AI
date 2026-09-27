"""Check whether the configured LLM provider actually works.

Run this whenever you are about to claim "AI" in a demo, a video or a submission:

    cd backend
    python check_llm.py

It makes one small live call and prints exactly what happened - including the
provider's own error text, which is the part you need to fix a bad key:

    - 400 / "API key not valid"      -> the key is wrong, regenerate it
    - 404 / "model not found"        -> LLM_MODEL is wrong for this provider
    - 429 / "quota"                  -> free-tier rate limit or daily cap reached
    - timeout                        -> network/firewall or the provider is down

Why this matters: `LLM_MODE=auto` degrades to the deterministic rule engine on
any failure, so a broken key is *invisible* at the product level - triage still
returns the correct RED/YELLOW/GREEN. That is good for safety and bad for
honesty: if the key is broken, the deployment is running no AI at all, and the
submission requires disclosing the real AI contribution.

For the deployed service, use the endpoint instead of this script:
    https://YOUR-SERVICE.onrender.com/api/admin/llm-check
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config import get_settings  # noqa: E402
from llm.client import probe_llm  # noqa: E402


def main() -> int:
    settings = get_settings()
    print("MediTriage AI - LLM connectivity check")
    print("=" * 68)
    print(f"provider        : {settings.provider}")
    print(f"model           : {settings.effective_model or '(none)'}")
    print(f"LLM_MODE        : {settings.llm_mode}")
    print(f"key present     : {settings._provider_key_present()}")
    print(f"ollama base url : {settings.ollama_base_url}")
    print("-" * 68)

    if settings.llm_mode == "off":
        print("LLM_MODE=off - the system is intentionally deterministic.")
        print("Set LLM_MODE=auto to enable the provider.")
        return 0

    if not settings.llm_available:
        print("No LLM configured, so nothing to test.")
        print(f"reason: {settings._llm_reason()}")
        print("\nThe system is fully functional without an LLM: triage comes from")
        print("the deterministic rule engine. Add a key only if you want AI")
        print("structuring and phrasing as well.")
        return 0

    print("Making one live call...")
    result = probe_llm()

    if result["ok"]:
        print("\nRESULT: WORKING")
        print(f"  provider replied    : {(result['sample'] or '').strip()[:80]!r}")
        print("  The AI layer is live. Disclose the provider and model in your submission.")
        return 0

    print("\nRESULT: FAILING - the deployment is running the deterministic engine only.")
    print(f"  reason: {result['error']}")
    print("\nCommon causes:")
    print("  - API key wrong, revoked or from the wrong project -> regenerate it")
    print("  - LLM_MODEL not available to this key/region         -> try the alternative IDs")
    print("  - free-tier quota/rate limit reached                 -> wait, or use another provider")
    print("  - Ollama selected but no local server                -> run `ollama serve`")
    print("\nThis does NOT break the demo: triage is decided by the rule engine either way.")
    print("But if you present AI as a feature, fix this first or disclose that it is off.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
