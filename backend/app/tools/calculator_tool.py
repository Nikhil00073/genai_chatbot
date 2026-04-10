# WAY 3 — using StructuredTool for full control
# Use this when you want to add extra validation or metadata

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# define the input schema using Pydantic
class CalculatorInput(BaseModel):
    expression: str = Field(
        description="A valid Python math expression like '2 + 2' or '10 * 5 / 2'"
    )


def _run_calculator(expression: str) -> str:
    """
    Safely evaluates a math expression.
    Only allows numbers and basic operators — no code execution.
    """
    # whitelist only safe characters
    allowed = set("0123456789+-*/()., ")
    if not all(c in allowed for c in expression):
        return "Invalid expression — only numbers and +-*/() allowed."

    try:
        result = eval(expression)   # safe because we whitelisted chars
        return f"Result of {expression} = {result}"
    except Exception as e:
        return f"Could not calculate: {str(e)}"


# StructuredTool gives you full control over name, description, schema
calculator = StructuredTool.from_function(
    func=_run_calculator,
    name="calculator",
    description=(
        "Calculates math expressions. "
        "Use this when the user asks for any calculation, "
        "arithmetic, or number computation. "
        "Input must be a valid math expression like '15 * 3 + 10'."
    ),
    args_schema=CalculatorInput,
)