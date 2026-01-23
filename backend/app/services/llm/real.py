from .base import LLMClient


class RealLLMClient(LLMClient):
    def generate_answer(self, query: str, context: str) -> str:
        raise NotImplementedError("RealLLMClient is not implemented in Phase 1")