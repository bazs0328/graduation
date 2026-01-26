from typing import Dict

from app.core.config import Settings

from .base import ToolSpec
from .safe_calc import calc_tool


def _normalize_whitelist(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def build_tool_registry(settings: Settings) -> Dict[str, ToolSpec]:
    if not settings.llm_tools_enabled:
        return {}

    available = {
        calc_tool.name: calc_tool,
    }

    whitelist = _normalize_whitelist(settings.llm_tool_whitelist)
    if not whitelist:
        return {}

    if "*" in whitelist or "all" in whitelist:
        return available

    allowed: Dict[str, ToolSpec] = {}
    for name in whitelist:
        tool = available.get(name)
        if tool:
            allowed[name] = tool
    return allowed
