import logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = logging.getLogger("gateway")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _provider_cfg(name: str) -> dict:
    if name == "deepseek":
        return dict(api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                    model=settings.deepseek_model)
    if name == "groq":
        return dict(api_key=settings.groq_api_key,
                    base_url=GROQ_BASE_URL,
                    model=settings.groq_model)
    raise ValueError(f"Unknown provider: {name}")


class LLMGateway:
    def __init__(self):
        primary = settings.llm_provider
        secondary = "groq" if primary == "deepseek" else "deepseek"
        self.order = [primary, secondary]
        self._clients: dict[str, AsyncOpenAI] = {}

    def _client(self, name: str) -> tuple[AsyncOpenAI, str]:
        cfg = _provider_cfg(name)
        if name not in self._clients:
            self._clients[name] = AsyncOpenAI(
                api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=60
            )
        return self._clients[name], cfg["model"]

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
    async def _call(self, provider, messages, temperature, json_mode):
        client, model = self._client(provider)
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        res = await client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, **kwargs
        )
        return res.choices[0].message.content or ""

    async def chat(self, messages: list[dict], temperature: float = 0.2,
                   json_mode: bool = False) -> str:
        last_err = None
        for provider in self.order:
            if not _provider_cfg(provider)["api_key"]:
                continue
            try:
                return await self._call(provider, messages, temperature, json_mode)
            except Exception as e:  # fall through to next provider
                log.warning("LLM provider %s failed: %s", provider, e)
                last_err = e
        raise RuntimeError(f"All LLM providers failed: {last_err}")


llm = LLMGateway()