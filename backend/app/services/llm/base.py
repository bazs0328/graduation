from typing import Protocol


class LLMClient(Protocol):
    def generate_answer(self, query: str, context: str) -> str:
        ...