from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Protocol

import httpx

from literary_intelligence.schemas.llm_pass import LLMPassOutput, PassName

from .prompts import build_messages


class LLMUnavailableError(RuntimeError):
    """The local LLM is not available or no LI-1 adapter is configured."""


class LLMClient(Protocol):
    def complete(self, pass_name: PassName, context: dict) -> LLMPassOutput:
        ...


class MockLLMClient:
    """Fixture-backed client used by LI-1 tests.

    Mock output is never evidence of real model capability.
    """

    def __init__(self, fixture_path: Path):
        self.fixture_path = Path(fixture_path)
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        passes = data.get("passes")
        if not isinstance(passes, dict):
            raise ValueError(f"Mock fixture must contain a passes mapping: {self.fixture_path}")
        self._passes = passes

    def complete(self, pass_name: PassName, context: dict) -> LLMPassOutput:
        if pass_name not in self._passes:
            raise LLMUnavailableError(f"No mock output for pass: {pass_name}")
        output = LLMPassOutput.model_validate(self._passes[pass_name])
        if output.pass_name != pass_name:
            raise ValueError(f"Mock pass mismatch: requested {pass_name}, got {output.pass_name}")
        return output.model_copy(update={"is_mock": True})


class UnavailableLLMClient:
    """Explicitly unavailable local model.

    Use this only when the 8080 service is down; it must never stand in for a
    real call while the endpoint is up.
    """

    def complete(self, pass_name: PassName, context: dict) -> LLMPassOutput:
        raise LLMUnavailableError(
            "Real local LLM is NOT_RUN in LI-1; use MockLLMClient or inject a "
            "verified local adapter via LocalLLMClient."
        )


class LocalLLMClient:
    """Adapter for a verified local model transport.

    The caller supplies ``invoke(pass_name, context) -> mapping``. This keeps
    endpoint/API-format decisions outside LI-1; the verified project LLM at
    :8080 (``Qwen3-30B-A3B-Instruct-2507``, 64K context, CPU-only) is wired
    through :class:`OpenAICompatibleLLMClient`.
    """

    def __init__(self, invoke: Callable[[PassName, dict], dict]):
        self._invoke = invoke

    def complete(self, pass_name: PassName, context: dict) -> LLMPassOutput:
        output = LLMPassOutput.model_validate(self._invoke(pass_name, context))
        if output.pass_name != pass_name:
            raise ValueError(f"Local LLM pass mismatch: requested {pass_name}, got {output.pass_name}")
        return output


class LLMResponseError(RuntimeError):
    """The model returned text that is not the requested JSON contract."""


def parse_json_response(text: str) -> dict:
    """Extract one JSON object from a model response, including /think tails."""
    content = text.strip()
    if "<｜end▁of▁thinking｜>" in content:
        content = content.split("<｜end▁of▁thinking｜>", 1)[1].strip()
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    if content.startswith("```"):
        content = content.split(chr(10), 1)[1] if chr(10) in content else content
        if content.endswith("```"):
            content = content[:-3].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        raise LLMResponseError("No JSON object found in model response: " + content[:1200])
    try:
        value = json.loads(content[start:end + 1])
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Invalid JSON in model response: {exc}; response={content[start:start+1200]!r}") from exc
    if not isinstance(value, dict):
        raise LLMResponseError("Model response JSON must be an object")
    return value


class OpenAICompatibleLLMClient:
    """Real local llama.cpp client for the existing 8080 endpoint.

    The endpoint comes from project settings (or explicit arguments); no URL is
    hardcoded here. The model must return the LI-1 JSON contract.

    Verified 2026-11-03: 8080 serves ``Qwen3-30B-A3B-Instruct-2507``
    CPU-only (``-ngl 0``) with ``-c 65536`` (64K).
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str = "",
        timeout_s: float = 600.0,
        max_tokens: int = 1000,
        temperature: float = 0.2,
        http_client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = http_client or httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_s),
            trust_env=False,
        )

    def complete(self, pass_name: PassName, context: dict) -> LLMPassOutput:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = self._client.post(
            "/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": build_messages(pass_name, context),
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(f"Unexpected chat completion shape: {data}") from exc
        output = LLMPassOutput.model_validate(parse_json_response(content))
        if output.pass_name != pass_name:
            raise LLMResponseError(
                f"Model returned pass_name={output.pass_name}, expected {pass_name}"
            )
        return output.model_copy(update={"is_mock": False, "raw_response": content})
