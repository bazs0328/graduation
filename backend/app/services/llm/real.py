import json
import re
import time
from typing import Any, Tuple

import httpx

from app.services.provider_utils import normalize_base_url
from app.services.tools import ToolRunError, ToolSpec

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
        raw_json = False
        if query.startswith("RAW_JSON:"):
            raw_json = True
            query = query[len("RAW_JSON:"):].lstrip()

        cleaned = (context or "").strip()
        if not cleaned and not raw_json:
            return "资料中未找到相关内容"

        if raw_json:
            system_prompt = "你是严格的JSON生成器。只输出JSON，不要任何多余文本。"
            user_prompt = query
        else:
            system_prompt = "你是学习助手。请仅基于提供的资料回答问题，避免引入资料之外的信息。"
            user_prompt = f"问题：{query}\n\n资料：\n{cleaned}\n\n请用简洁中文回答。"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": self.max_tokens if not raw_json else max(self.max_tokens, 800),
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
        if raw_json and not content:
            reasoning = (message.get("reasoning_content") or "").strip()
            if reasoning:
                matches = re.findall(r"\{.*\}", reasoning, re.DOTALL)
                if matches:
                    content = matches[-1].strip()
        if not content:
            raise RuntimeError("LLM response missing content.")
        return content

    def generate_answer_with_tools(
        self,
        query: str,
        context: str,
        tools: list[Any],
        max_calls: int,
        forced_tool: str | None = None,
    ) -> Tuple[str, list[dict]]:
        tool_specs = [tool for tool in tools if isinstance(tool, ToolSpec)]
        if not tool_specs or max_calls <= 0:
            return self.generate_answer(query, context), []

        tool_map = {tool.name: tool for tool in tool_specs}
        tool_schemas = [tool.openai_schema() for tool in tool_specs]
        tool_traces: list[dict] = []

        cleaned = (context or "").strip()
        if not cleaned and not forced_tool:
            return "资料中未找到相关内容", []

        system_prompt = "你是学习助手。必要时可调用工具，但必须保证引用可追溯。"
        user_prompt = f"问题：{query}\n\n资料：\n{cleaned}\n\n请用简洁中文回答。"
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        headers = {"Authorization": f"Bearer {self.api_key}"}
        tool_choice: Any = "auto"
        if forced_tool and forced_tool in tool_map:
            tool_choice = {"type": "function", "function": {"name": forced_tool}}

        with httpx.Client(timeout=self.timeout) as client:
            for _ in range(max_calls):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": self.max_tokens,
                    "tools": tool_schemas,
                    "tool_choice": tool_choice,
                }
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
                tool_calls = message.get("tool_calls") or []
                content = (message.get("content") or "").strip()

                if tool_calls:
                    messages.append({"role": "assistant", "tool_calls": tool_calls})
                    for call in tool_calls:
                        func = call.get("function") or {}
                        tool_name = func.get("name")
                        call_id = call.get("id") or ""
                        raw_args = func.get("arguments") or "{}"
                        start = time.perf_counter()
                        trace = {
                            "tool_name": tool_name,
                            "input": raw_args,
                            "output": None,
                            "error": None,
                            "duration_ms": None,
                        }
                        try:
                            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                            trace["input"] = args
                            tool = tool_map.get(tool_name)
                            if not tool:
                                raise ToolRunError("Tool not allowed.")
                            output = tool.run(args)
                            trace["output"] = output
                        except (json.JSONDecodeError, ToolRunError, ValueError) as exc:
                            trace["error"] = str(exc)
                            output = f"ERROR: {exc}"
                        except Exception as exc:
                            trace["error"] = f"Unexpected error: {exc}"
                            output = f"ERROR: {exc}"
                        finally:
                            trace["duration_ms"] = int((time.perf_counter() - start) * 1000)
                            tool_traces.append(trace)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call_id,
                                "content": output,
                            }
                        )
                    tool_choice = "auto"
                    continue

                if content:
                    return content, tool_traces

        return self.generate_answer(query, context), tool_traces
