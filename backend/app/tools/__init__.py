# export all tools from one place
# agent_service.py imports from here
from .search_tool import search_docs
from .weather_tool import get_weather
from .calculator_tool import calculator

ALL_TOOLS = [search_docs, get_weather, calculator]