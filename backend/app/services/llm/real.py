import httpx

from app.services.provider_utils import normalize_base_url

from .base import LLMClient


class RealLLMClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        max_tokens: int = 512,
    ):
        self.base_url = normalize_base_url(base_url)
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate_answer(self, query: str, context: str) -> str:
        cleaned = (context or "").strip()
        if not cleaned:
            return "资料中未找到相关内容"

        system_prompt = "你是学习助手。请仅基于提供的资料回答问题，避免引入资料之外的信息。"
        user_prompt = f"问题：{query}\n\n资料：\n{cleaned}\n\n请用简洁中文回答。"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("LLM response missing choices.")
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise RuntimeError("LLM response missing content.")
        return content
