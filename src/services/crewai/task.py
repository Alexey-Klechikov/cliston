import logging

from crewai import Agent, Task

from agents import TaskConfig


def compose_task(agent: Agent, task_config: TaskConfig) -> Task:
    """Create a fresh Task for each crew build to avoid stale runtime variables."""
    key = f"{agent.role}:{task_config.name}"
    task = Task(
        description=task_config.description,
        expected_output=task_config.expected_output,
        agent=agent,
    )
    logging.info("Task '%s' initialised", key)
    return task
