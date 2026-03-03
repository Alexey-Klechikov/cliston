import logging

from services.crewai.crew import build_crew
from services.crewai.models import CrewResponse
from settings.agents import CLISTON_CONFIG, MTB_CONFIG


async def process_message(user_message: str) -> CrewResponse:
    """Public entry-point: build a crew, kick it off, and return a response."""
    crew = build_crew(agents_configs=[CLISTON_CONFIG, MTB_CONFIG])
    output = crew.kickoff(inputs={"topic": user_message})

    logging.info("Crew finished for message: %.80s...", user_message)

    return CrewResponse(response=str(output))
