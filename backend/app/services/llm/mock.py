import re
from typing import Any, List, Tuple

from app.services.tools import ToolRunError, ToolSpec

from .base import LLMClient


class MockLLM(LLMClient):
    def __init__(self, max_points: int = 4):
        self.max_points = max_points

    def generate_answer(self, query: str, context: str) -> str:
        if query.startswith("RAW_JSON:"):
            return "{\"conclusion\":\"资料中未找到相关内容\",\"evidence\":[],\"reasoning\":\"\",\"next_steps\":[]}"
        cleaned = context.strip()
        if not cleaned:
            return "资料中未找到相关内容"

        text = cleaned.replace("\n", " ")
        parts = re.split(r"[。！？.!?;；]+", text)
        points: List[str] = []
        for part in parts:
            part = part.strip()
            if part and part not in points:
                points.append(part)
            if len(points) >= self.max_points:
                break

        if not points:
            return "资料中未找到相关内容"

        return "根据资料：" + "；".join(points)

    def generate_answer_with_tools(
        self,
        query: str,
        context: str,
        tools: list[Any],
        max_calls: int,
        forced_tool: str | None = None,
    ) -> Tuple[str, list[dict]]:
        if not tools or max_calls <= 0:
            return self.generate_answer(query, context), []

        tool_map = {
            tool.name: tool for tool in tools if isinstance(tool, ToolSpec)
        }

        expr = _extract_calc_expression(query)
        tool_name = forced_tool or ("calc" if expr else None)
        if not tool_name or tool_name not in tool_map or not expr:
            return self.generate_answer(query, context), []

        trace = {"tool_name": tool_name, "input": {"expression": expr}}
        try:
            output = tool_map[tool_name].run({"expression": expr})
            trace["output"] = output
            trace["error"] = None
            return f"计算结果：{output}", [trace]
        except ToolRunError as exc:
            trace["output"] = None
            trace["error"] = str(exc)
            return f"计算失败：{exc}", [trace]


def _extract_calc_expression(query: str) -> str | None:
    if not query:
        return None
    trimmed = query.strip()
    lowered = trimmed.lower()
    if lowered.startswith("calc:"):
        return trimmed.split(":", 1)[1].strip()
    if trimmed.startswith("计算"):
        return trimmed[2:].strip()
    return None
