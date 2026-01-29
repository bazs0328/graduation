from typing import Any, Protocol, Tuple


class LLMClient(Protocol):
    def generate_answer(self, query: str, context: str) -> str:
        ...

    def generate_answer_with_tools(
        self,
        query: str,
        context: str,
        tools: list[Any],
        max_calls: int,
        forced_tool: str | None = None,
    ) -> Tuple[str, list[dict]]:
        ...
