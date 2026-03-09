import logging

from crewai import Agent
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from agents import AgentConfig
from services.crewai.llm import get_llm


@tool("DuckDuckGoSearch")
def managed_search(search_query: str) -> str:
    """Search the internet for information on a specific topic."""
    return DuckDuckGoSearchRun().run(search_query)


_agents: dict[str, Agent] = {}


def get_agent(config: AgentConfig) -> Agent:
    """Return (or create) a singleton Agent for the given config role."""
    if config.role not in _agents:
        tools = []
        if config.allow_search:
            tools.append(managed_search)

        _agents[config.role] = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=tools,
            verbose=config.verbose,
            llm=get_llm(),
            allow_delegation=False,
        )

        logging.info("Agent '%s' initialised", config.role)

    return _agents[config.role]
