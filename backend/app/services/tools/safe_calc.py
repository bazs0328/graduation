import ast
import math
from typing import Any, Dict

from .base import ToolRunError, ToolSpec


_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}

_ALLOWED_UNARY = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}

_ALLOWED_NAMES = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ToolRunError("Only numeric constants are allowed.")
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_NAMES:
            return float(_ALLOWED_NAMES[node.id])
        raise ToolRunError("Unknown identifier in expression.")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ToolRunError("Operator not allowed.")
        return _ALLOWED_BINOPS[op_type](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY:
            raise ToolRunError("Unary operator not allowed.")
        return _ALLOWED_UNARY[op_type](_eval_node(node.operand))
    raise ToolRunError("Unsupported expression.")


def safe_calc(expression: str) -> str:
    expr = (expression or "").strip()
    if not expr:
        raise ToolRunError("Expression is required.")
    if len(expr) > 200:
        raise ToolRunError("Expression too long.")
    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ToolRunError("Invalid expression.") from exc
    result = _eval_node(node)
    if math.isinf(result) or math.isnan(result):
        raise ToolRunError("Invalid numeric result.")
    if result.is_integer():
        return str(int(result))
    return str(round(result, 10)).rstrip("0").rstrip(".")


def _calc_handler(arguments: Dict[str, Any]) -> str:
    expression = arguments.get("expression")
    if not isinstance(expression, str):
        raise ToolRunError("expression must be a string")
    return safe_calc(expression)


calc_tool = ToolSpec(
    name="calc",
    description="安全计算器：支持基本四则运算与幂运算，支持常量 pi 和 e。",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，例如 1+2*(3+4) 或 pi*2",
            }
        },
        "required": ["expression"],
    },
    handler=_calc_handler,
)
