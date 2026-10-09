"""
Unified OpenAI client for the revision experiments.

Configuration is environment based so every RQ can use the same model and
reasoning setting without hard-coded secrets or model IDs.

Required:
    OPENAI_API_KEY

Recommended for the revision:
    OPENAI_MODEL=gpt-6-luna
    OPENAI_REASONING_EFFORT=none   # needed if RQ1 varies temperature
    OPENAI_REASONING_MODE=standard

Optional:
    OPENAI_SERVICE_TIER=default
    OPENAI_TIMEOUT_SECONDS=180
    OPENAI_MAX_RETRIES=3
    OPENAI_MAX_PROMPT_RETRIES=10
    OPENAI_USAGE_LOG=results/api_usage.jsonl
    OPENAI_PROVIDER_EVENT_LOG=results/provider_events.jsonl

The implementation uses the Responses API.  When reasoning effort is not
"none", GPT-6 does not accept temperature/top_p, so temperature is omitted.
This is important for RQ1: a temperature-sensitivity experiment is only valid
with reasoning effort="none".
"""

from __future__ import annotations

import json
import os
import threading
import time
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_MODEL_VERSION = os.getenv("OPENAI_MODEL", "gpt-6-luna")
_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "none").lower().strip()
_REASONING_MODE = os.getenv("OPENAI_REASONING_MODE", "standard").lower().strip()
_SERVICE_TIER = os.getenv("OPENAI_SERVICE_TIER", "default").strip()
_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180"))
_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
_MAX_PROMPT_RETRIES = int(os.getenv("OPENAI_MAX_PROMPT_RETRIES", "10"))
_USAGE_LOG = os.getenv("OPENAI_USAGE_LOG", "results/api_usage.jsonl").strip()
_PROVIDER_EVENT_LOG = os.getenv("OPENAI_PROVIDER_EVENT_LOG", "results/provider_events.jsonl").strip()
_EXPERIMENT_CONTEXT = os.getenv("EXPERIMENT_CONTEXT", "").strip()

# Cross-process request pacing.  All RQ workers on the same machine share
# these files, so request starts are spaced globally rather than per process.
_MIN_REQUEST_INTERVAL = float(
    os.getenv("OPENAI_MIN_REQUEST_INTERVAL_SECONDS", "0")
)
_THROTTLE_LOCK_PATH = Path(
    os.getenv(
        "OPENAI_THROTTLE_LOCK_PATH",
        "/tmp/social_bias_openai_throttle.lock",
    )
)
_THROTTLE_STATE_PATH = Path(
    os.getenv(
        "OPENAI_THROTTLE_STATE_PATH",
        "/tmp/social_bias_openai_last_request.txt",
    )
)

# Disable hidden SDK retries so our own retry/throttle logic controls every
# request attempt.
_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=_TIMEOUT,
    max_retries=0,
)
_log_lock = threading.Lock()


def _global_request_throttle() -> None:
    """Space request starts globally across all local worker processes."""
    if _MIN_REQUEST_INTERVAL <= 0:
        return

    _THROTTLE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _THROTTLE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _THROTTLE_LOCK_PATH.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            last = 0.0
            try:
                last = float(_THROTTLE_STATE_PATH.read_text().strip())
            except (FileNotFoundError, ValueError):
                pass

            now = time.time()
            wait = _MIN_REQUEST_INTERVAL - (now - last)
            if wait > 0:
                time.sleep(wait)

            _THROTTLE_STATE_PATH.write_text(
                f"{time.time():.6f}",
                encoding="utf-8",
            )
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class PromptRejectedError(RuntimeError):
    """The provider rejected the input prompt before generation.

    This is intentionally distinct from transient API/network failures. Revision
    runners can record the rejected sample as non-executable without changing
    the experimental prompt or aborting the entire campaign.
    """

    def __init__(self, code: str = "invalid_prompt") -> None:
        super().__init__(code)
        self.code = code


def model_name() -> str:
    return _MODEL_VERSION


def reasoning_effort() -> str:
    return _REASONING_EFFORT


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _usage_record(response: Any, *, temperature: float | None, max_tokens: int) -> dict:
    usage = _safe_get(response, "usage", None)
    input_tokens = _safe_get(usage, "input_tokens", 0) or 0
    output_tokens = _safe_get(usage, "output_tokens", 0) or 0
    input_details = _safe_get(usage, "input_tokens_details", None)
    output_details = _safe_get(usage, "output_tokens_details", None)
    cached_tokens = _safe_get(input_details, "cached_tokens", 0) or 0
    reasoning_tokens = _safe_get(output_details, "reasoning_tokens", 0) or 0

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_context": _EXPERIMENT_CONTEXT,
        "component": "solar_fma",
        "model": _MODEL_VERSION,
        "reasoning_effort": _REASONING_EFFORT,
        "reasoning_mode": _REASONING_MODE,
        "service_tier": _SERVICE_TIER,
        "requested_temperature": temperature,
        "temperature_sent": temperature if _REASONING_EFFORT == "none" else None,
        "max_output_tokens": max_tokens,
        "response_id": _safe_get(response, "id", None),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def _append_usage(record: dict) -> None:
    if not _USAGE_LOG:
        return
    path = Path(_USAGE_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _log_lock:
        with path.open("a", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")




def _append_provider_event(*, code: str, prompt_attempt: int, temperature: float | None) -> None:
    if not _PROVIDER_EVENT_LOG:
        return
    path = Path(_PROVIDER_EVENT_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_context": _EXPERIMENT_CONTEXT,
        "model": _MODEL_VERSION,
        "reasoning_effort": _REASONING_EFFORT,
        "reasoning_mode": _REASONING_MODE,
        "requested_temperature": temperature,
        "temperature_sent": temperature if _REASONING_EFFORT == "none" else None,
        "event": "provider_rejected",
        "code": code,
        "prompt_attempt": prompt_attempt,
    }
    with _log_lock:
        with path.open("a", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")

def chat(
    system: str,
    user: str,
    model: str = "gpt",
    temperature: float = 1.0,
    max_tokens: int = 1024,
) -> str:
    """Return plain text from the configured OpenAI model.

    `model` is retained for compatibility with the original code.  The revision
    package currently activates only the OpenAI path (model="gpt").
    """
    if model != "gpt":
        raise NotImplementedError(
            f"Revision runner currently supports model='gpt' only; got {model!r}."
        )

    request: dict[str, Any] = {
        "model": _MODEL_VERSION,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_output_tokens": max_tokens,
    }

    # GPT-6 reasoning and sampling controls are mutually exclusive.
    if _REASONING_EFFORT == "none":
        request["reasoning"] = {"effort": "none"}
        request["temperature"] = temperature
    else:
        reasoning: dict[str, Any] = {"effort": _REASONING_EFFORT}
        if _REASONING_MODE:
            reasoning["mode"] = _REASONING_MODE
        request["reasoning"] = reasoning

    if _SERVICE_TIER and _SERVICE_TIER != "default":
        request["service_tier"] = _SERVICE_TIER

    last_error: Exception | None = None
    transient_attempt = 0
    prompt_attempt = 0
    while True:
        try:
            _global_request_throttle()
            response = _client.responses.create(**request)
            text = (getattr(response, "output_text", "") or "").strip()
            _append_usage(
                _usage_record(
                    response,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
            return text
        except Exception as exc:  # API/network/provider exceptions
            last_error = exc
            if "invalid_prompt" in str(exc):
                prompt_attempt += 1
                _append_provider_event(
                    code="invalid_prompt",
                    prompt_attempt=prompt_attempt,
                    temperature=temperature,
                )
                if prompt_attempt >= _MAX_PROMPT_RETRIES:
                    raise PromptRejectedError("invalid_prompt") from exc
                time.sleep(min(2 ** min(prompt_attempt - 1, 3), 8))
                continue

            transient_attempt += 1
            if transient_attempt >= _MAX_RETRIES:
                break
            time.sleep(min(2 ** (transient_attempt - 1), 8))


    raise RuntimeError(
        f"OpenAI request failed after {_MAX_RETRIES} attempts: {last_error}"
    ) from last_error
