"""Providerul unic pentru conversațiile educaționale Qwen din aplicație."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "qwen/qwen3.7-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _read_local_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _openrouter_api_key() -> str:
    if os.getenv("OPENROUTER_API_KEY"):
        return str(os.environ["OPENROUTER_API_KEY"]).strip()
    candidates = (
        ROOT_DIR / "cercetare-qwen" / "config.local.env",
        ROOT_DIR / "cercetare" / "experiment2" / "config.local.env",
    )
    for path in candidates:
        key = _read_local_env(path).get("OPENROUTER_API_KEY", "").strip()
        if key:
            return key
    return ""


class OpenRouterProvider:
    """Trimite toate răspunsurile interactive la Qwen 3.7 Flash."""

    def __init__(self) -> None:
        self.api_key = _openrouter_api_key()
        self.model = os.getenv("QWEN_CHAT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.timeout = int(os.getenv("OPENROUTER_CHAT_TIMEOUT", "180"))
        if not self.api_key:
            raise RuntimeError(
                "Lipsește OPENROUTER_API_KEY. Adaugă cheia în config.local.env."
            )

    def _generate(
        self,
        prompt: str,
        *,
        json_mode: bool = False,
        max_tokens: int = 3000,
        reasoning_effort: str = "medium",
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.25,
            "max_tokens": max_tokens,
            "reasoning": {"effort": reasoning_effort, "exclude": True},
            "provider": {
                "allow_fallbacks": True,
                "require_parameters": True,
                "data_collection": "deny",
            },
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost/bacapp",
                "X-Title": "BacApp",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"OpenRouter a răspuns cu HTTP {error.code}: {detail}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"OpenRouter nu poate fi contactat: {error.reason}") from error
        try:
            choice = result["choices"][0]
            if choice.get("finish_reason") == "length":
                raise RuntimeError(
                    "OpenRouter a întrerupt răspunsul deoarece a atins limita de tokeni."
                )
            return str(choice["message"]["content"] or "")
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("OpenRouter nu a returnat un răspuns Qwen utilizabil.") from error

    def generate_text(self, prompt: str) -> str:
        return self._generate(prompt)

    def generate_chat_text(self, prompt: str) -> str:
        """Generează răspunsuri conversaționale fără a consuma bugetul pe raționament lung."""
        return self._generate(
            prompt,
            max_tokens=6000,
            reasoning_effort="low",
        )

    def generate_json(self, prompt: str, response_schema: dict | None = None) -> str:
        schema_note = (
            "\n\nRespectă această schemă JSON:\n"
            + json.dumps(response_schema, ensure_ascii=False)
            if response_schema
            else ""
        )
        return self._generate(prompt + schema_note, json_mode=True)
