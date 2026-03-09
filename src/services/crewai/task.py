import logging

from crewai import Task, Agent

from agents import TaskConfig


_tasks: dict[str, Task] = {}


def compose_task(agent: Agent, task_config: TaskConfig) -> Task:
    """Return (or create) a singleton Task for the given role and task name."""
    key = f"{agent.role}:{task_config.name}"
    if key not in _tasks:
        _tasks[key] = Task(
            description=task_config.description,
            expected_output=task_config.expected_output,
            agent=agent,
        )
        logging.info("Task '%s' initialised", key)

    return _tasks[key]
