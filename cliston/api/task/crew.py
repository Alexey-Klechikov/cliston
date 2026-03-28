import logging

from agents import AgentConfig
from crewai import Crew, Process

from cliston.api.task.agent import get_agent
from cliston.api.task.task import compose_task


def build_crew(agents_configs: list[AgentConfig], task_id: str) -> Crew:
    """Assemble the crew for a single user request."""

    crew_agents = []
    crew_tasks = []
    for agent_config in agents_configs:
        agent = get_agent(agent_config)
        crew_agents.append(agent)

        for task_config in agent_config.tasks_configs:
            task = compose_task(agent=agent, task_config=task_config, task_id=task_id)
            crew_tasks.append(task)

    crew = Crew(
        agents=crew_agents,  # type: ignore
        tasks=crew_tasks,
        process=Process.sequential,
        memory=False,
        cache=True,
        verbose=True,
    )

    logging.info("Crew assembled with %d agents and %d tasks", len(crew_agents), len(crew_tasks))
    return crew
