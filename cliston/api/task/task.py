import logging
from functools import partial

from agents import TaskConfig
from crewai import Agent, Task
from services.logging.operators import log_task_output


def compose_task(agent: Agent, task_config: TaskConfig, task_id: str) -> Task:
    """Create a fresh Task for each crew build to avoid stale runtime variables."""

    key = f"{agent.role}:{task_config.name}"
    task = Task(
        agent=agent,
        description=task_config.description,
        expected_output=task_config.expected_output,
        callback=partial(log_task_output, agent.role, task_id=task_id),
    )
    logging.info("Task '%s' initialised", key)
    return task
