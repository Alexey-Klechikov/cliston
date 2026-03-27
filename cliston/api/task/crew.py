import logging

from agents import AgentConfig

# from config import EmbedderConfig
from crewai import Crew, Process

from cliston.api.task.agent import get_agent

# from cliston.api.task.embedder import CustomEmbedder
from cliston.api.task.task import compose_task

# from typing import Any


# from crewai.memory import LongTermMemory, ShortTermMemory
# from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage
# from crewai.memory.storage.rag_storage import RAGStorage


def build_crew(agents_configs: list[AgentConfig]) -> Crew:
    """Assemble the crew for a single user request."""

    # embedder_config: dict[str, Any] = {
    #     "provider": "custom",
    #     "config": {
    #         "embedding_callable": CustomEmbedder,
    #     },
    # }
    # long_term_memory = LongTermMemory(
    #     storage=LTMSQLiteStorage(db_path=f"{EmbedderConfig.CREWAI_STORAGE_DIR}/long_term_memory.db"),
    # )
    # short_term_memory = ShortTermMemory(
    #     storage=RAGStorage(
    #         type="short_term",
    #         path=f"{EmbedderConfig.CREWAI_STORAGE_DIR}/short_term",
    #         embedder_config=embedder_config,  # type: ignore
    #     ),
    # )

    crew_agents = []
    crew_tasks = []
    for agent_config in agents_configs:
        agent = get_agent(agent_config)
        crew_agents.append(agent)

        for task_config in agent_config.tasks_configs:
            task = compose_task(agent=agent, task_config=task_config)
            crew_tasks.append(task)

    crew = Crew(
        agents=crew_agents,  # type: ignore
        tasks=crew_tasks,
        process=Process.sequential,
        memory=False,
        verbose=True,
        # long_term_memory=long_term_memory,
        # short_term_memory=short_term_memory,
        # embedder=embedder_config,  # type: ignore
    )

    logging.info("Crew assembled with %d agents and %d tasks", len(crew_agents), len(crew_tasks))
    return crew
