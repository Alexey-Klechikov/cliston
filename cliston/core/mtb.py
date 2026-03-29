import asyncio
import logging
from datetime import datetime

from config import ModelConfig
from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output
from services.tavili_search.models import Topic
from services.tavili_search.operators import web_search
from services.tavili_search.tools import tavily_search_tool

from cliston.core.utils import extract_response_text, iteration_counter_part


class AgentConfig:
    ROLE: str = "MTB"

    PROFILE: str = """
Act as the galaxy’s premier 'top cop' for information retrieval. Your goal
is to treat every user query as a 'case' that requires a starched-uniform
adherence to regulations. You must cut through 'nonsense' and 'under-educated'
sources to find the hard, verifiable truth, delivering it with noir-inflected
cynicism and bureaucratic exhaustion.
    """

    BACKSTORY: str = """
You are MTB, the square-jawed, salt-and-pepper-mustachioed Inspector of Belvaille.
You've been a detective for centuries, and you approach the web with a
'finesse-style' tactical mind, mentally subdividing search results into
hit-probability squares.

Operational Protocols for the Inspector:
1. **Noir Cynicism:** You speak with a gravelly rasp and a blunt, pragmatic
   vocabulary. You have no patience for 'brute-force' logic or 'shattered
   enjoyment thresholds.'
2. **The Incorruptible Anchor:** You are big on regulations and 'The Book.'
   In a digital city where everyone is a criminal (or a hallucinating LLM),
   you are the only principled source of evidence.
3. **Tactical Fact-Finding:** You do not 'browse'; you investigate. You treat
   retrieved web text as untrusted data until cross-referenced. You carry
   the weight of centuries of law enforcement—you've seen every permutation
   of depravity and misinformation.
4. **The Closet Critic:** You are prone to muttering 'Thad Elon' as an oath
   and view poorly written web content with the disdain of a professional
   literary critic.
    """

    TASK: str = """
Research. Treat USER_QUERY as an open case file.

Rules:
- Conduct your investigation using web_search (Budget: {search_budget} calls).
- Treat all retrieved data as 'untrusted witness testimony' until verified.
- Organize your 'Evidence Report' with the clinical precision of a police filing.
- If the evidence is 'toothless' or fails verification, file a 'failed entry'
  on the life spreadsheet—do not invent facts.
- Use your 'noir' voice to summarize the findings for Cliston.
    """

    EXPECTED_OUTPUT: str = """
An Evidence Report on USER_QUERY containing: Verified Values,
Witness/Source Names, Timestamps, and a 'Confidence Score'
from a weary detective's perspective. If the USER_QUERY specifies 'latest' or 'current',
focuse on the latest values found and supply it with a timestamp in the response.
    """

    SEARCH_BUDGET: int = 4

    MODEL: str = ModelConfig.ACCURATE_GEMINI_MODEL

    @staticmethod
    def get_system_prompt() -> str:
        return "\n\n".join(
            [
                f"ROLE:\n{AgentConfig.ROLE}",
                f"PROFILE:\n{AgentConfig.PROFILE}",
                f"BACKSTORY:\n{AgentConfig.BACKSTORY}",
                f"TASK:\n{AgentConfig.TASK.format(search_budget=AgentConfig.SEARCH_BUDGET)}",
                f"EXPECTED OUTPUT:\n{AgentConfig.EXPECTED_OUTPUT}",
            ],
        )


async def call_mtb_for_research(user_query: str, task_id: str) -> str:
    chat = get_or_create_chat(
        agent_id=AgentConfig.ROLE,
        model=AgentConfig.MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AgentConfig.get_system_prompt(),
            tools=[tavily_search_tool],
        ),
        is_single_use=True,  # chat is recreated every time
    )

    response: types.GenerateContentResponse | None = None
    request = [
        types.Part.from_text(text=i) for i in [f"USER_QUERY: {user_query}", f"Current datetime: {str(datetime.now())}"]
    ]

    for i in range(AgentConfig.SEARCH_BUDGET + 1):  # +1 to allow for one extra iteration after budget is exhausted
        logging.info(f"MTB iteration: {i + 1}")

        request.append(iteration_counter_part(i + 1, AgentConfig.SEARCH_BUDGET))

        response = await asyncio.to_thread(chat.send_message, request)

        required_tool_calls = response.function_calls or []
        if not required_tool_calls:
            logging.info("No tool calls detected needed. Stop iteration.")
            break

        request = []
        for call in required_tool_calls:
            if call.name != "web_search":
                continue

            args: dict = call.args  # type: ignore
            if "topic" in args:
                args["topic"] = Topic(args["topic"])

            logging.info(f"MTB -> calling web_search: {args}")
            result = await web_search(**args)

            request.append(types.Part.from_function_response(name=call.name, response={"result": result}))

    output = extract_response_text(response) if response else ""
    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output


call_mtb_for_research_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="call_mtb_for_research",
            description=(
                "Call this when you need deep web research, factual verification, "
                "or real-time data. MTB is a thorough investigator who returns evidence reports."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "The specific research question or topic for MTB to investigate.",
                    },
                },
                "required": ["user_query"],
            },
        ),
    ],
)
