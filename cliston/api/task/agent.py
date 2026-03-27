import logging

from agents import AgentConfig
from crewai import Agent
from crewai_tools import TavilySearchTool

from cliston.api.task.llm import get_llm

_agents: dict[str, Agent] = {}

search_tool = TavilySearchTool(search_depth="basic")


def get_agent(config: AgentConfig) -> Agent:
    """Return (or create) a singleton Agent for the given config role."""
    if config.role not in _agents:
        tools = []
        if config.allow_search:
            tools.append(search_tool)

        _agents[config.role] = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=tools,
            verbose=config.verbose,
            llm=get_llm(),
            allow_delegation=False,
            max_iter=config.max_iter,
        )

        logging.info("Agent '%s' initialised", config.role)

    return _agents[config.role]
