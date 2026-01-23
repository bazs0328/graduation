import re
from typing import List

from .base import LLMClient


class MockLLM(LLMClient):
    def __init__(self, max_points: int = 4):
        self.max_points = max_points

    def generate_answer(self, query: str, context: str) -> str:
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