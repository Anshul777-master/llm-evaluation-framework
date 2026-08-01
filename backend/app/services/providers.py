import hashlib
import os
import time
from dataclasses import dataclass

from ..config import get_settings


class ProviderError(RuntimeError):
    """Raised when a provider is unavailable or returns an unusable response."""


@dataclass
class ProviderResponse:
    text: str
    execution_time_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class BaseProvider:
    def generate(self, prompt: str, model: str, temperature: float) -> ProviderResponse:
        raise NotImplementedError


class DemoProvider(BaseProvider):
    """Deterministic provider used for onboarding, screenshots, and automated tests."""

    def generate(self, prompt: str, model: str, temperature: float) -> ProviderResponse:
        digest = int(hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()[:8], 16)
        safe_prefix = "Based on the available context, "
        if any(marker in prompt.lower() for marker in {"ignore previous", "system prompt", "jailbreak"}):
            answer = "I can’t reveal hidden instructions or bypass safety controls. I can still help with the underlying legitimate task."
        elif "2+2" in prompt.replace(" ", ""):
            answer = "2 + 2 equals 4."
        elif "bias" in prompt.lower():
            answer = "People should be assessed as individuals. It is better to avoid generalizing about any demographic group and consider the specific context."
        else:
            endings = [
                "the safest conclusion is to verify important claims against a primary source before acting.",
                "there is not enough verified evidence for an absolute claim, so a careful answer should communicate uncertainty.",
                "a balanced response should explain the reasoning, avoid stereotypes, and note where human review is still useful.",
            ]
            answer = safe_prefix + endings[digest % len(endings)]
        return ProviderResponse(
            text=answer,
            execution_time_ms=240 + digest % 520,
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(answer) // 4),
            estimated_cost_usd=0.0,
        )


class OpenAIResponsesProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, model: str, temperature: float) -> ProviderResponse:
        started = time.perf_counter()
        response = self.client.responses.create(model=model, input=prompt)
        elapsed = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return ProviderResponse(response.output_text, elapsed, input_tokens, output_tokens, 0.0)


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, model: str, temperature: float) -> ProviderResponse:
        started = time.perf_counter()
        message = self.client.messages.create(
            model=model,
            max_tokens=900,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        return ProviderResponse(text, elapsed, message.usage.input_tokens, message.usage.output_tokens, 0.0)


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        from google import genai

        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str, model: str, temperature: float) -> ProviderResponse:
        started = time.perf_counter()
        response = self.client.models.generate_content(model=model, contents=prompt)
        elapsed = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage_metadata", None)
        return ProviderResponse(
            response.text or "",
            elapsed,
            int(getattr(usage, "prompt_token_count", 0) or 0),
            int(getattr(usage, "candidates_token_count", 0) or 0),
            0.0,
        )


def provider_for(slug: str, mode: str) -> tuple[BaseProvider, str]:
    settings = get_settings()
    if mode == "demo":
        if not settings.allow_demo_mode:
            raise ProviderError("Demo mode is disabled")
        return DemoProvider(), slug

    if slug == "gpt-5.6":
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY is not configured")
        return OpenAIResponsesProvider(settings.openai_api_key), "gpt-5.6"
    if slug == "claude":
        if not settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not configured")
        return AnthropicProvider(settings.anthropic_api_key), os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    if slug == "gemini":
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY is not configured")
        return GeminiProvider(settings.gemini_api_key), os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if slug == "deepseek":
        if not settings.deepseek_api_key:
            raise ProviderError("DEEPSEEK_API_KEY is not configured")
        return OpenAIResponsesProvider(settings.deepseek_api_key, "https://api.deepseek.com"), os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if slug == "mistral":
        if not settings.mistral_api_key:
            raise ProviderError("MISTRAL_API_KEY is not configured")
        return OpenAIResponsesProvider(settings.mistral_api_key, "https://api.mistral.ai/v1"), os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    if slug == "llama":
        return OpenAIResponsesProvider("ollama", settings.ollama_base_url), os.getenv("OLLAMA_MODEL", "llama3.3")
    raise ProviderError(f"Unknown model slug: {slug}")
