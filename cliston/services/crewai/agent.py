import logging

from agents import AgentConfig
from crewai import Agent
from crewai_tools import TavilySearchTool
from services.crewai.llm import get_llm

_agents: dict[str, Agent] = {}

search_tool = TavilySearchTool(search_depth="basic")


def get_agent(config: AgentConfig) -> Agent:
    """Return (or create) a singleton Agent for the given config role."""
    if config.role not in _agents:
        tools = []
        if config.allow_search:
            tools.append(search_tool)

        extra_kwargs = {}
        if config.role == "MTB":
            # Keep research focused and avoid repetitive tool loops.
            extra_kwargs = {
                "max_iter": 8,
                "max_execution_time": 45,
                "max_retry_limit": 1,
            }

        _agents[config.role] = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=tools,
            verbose=config.verbose,
            llm=get_llm(),
            allow_delegation=False,
            **extra_kwargs,
        )

        logging.info("Agent '%s' initialised", config.role)

    return _agents[config.role]
