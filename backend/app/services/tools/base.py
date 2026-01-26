from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], str]

    def openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def run(self, arguments: Dict[str, Any]) -> str:
        return self.handler(arguments)


class ToolRunError(RuntimeError):
    pass
