import asyncio
import logging

from agents import CLISTON_CONFIG, MTB_CONFIG
from services.crewai.crew import build_crew
from services.crewai.models import CrewResponse


def _process_message_sync(user_message: str) -> CrewResponse:
    """Public entry-point: build a crew, kick it off, and return a response."""
    crew = build_crew(agents_configs=[CLISTON_CONFIG, MTB_CONFIG])
    output = crew.kickoff(inputs={"topic": user_message})

    logging.info("Crew finished for message: %s...", user_message)

    return CrewResponse(response=str(output))


async def process_message_background(user_message: str, task_id: str) -> None:
    try:
        result = await asyncio.to_thread(_process_message_sync, user_message)
        logging.info("Task %s completed. Result: %s", task_id, result.response)

    except Exception:
        logging.exception("Task %s failed", task_id)
