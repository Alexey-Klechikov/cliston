import asyncio
import logging
from datetime import datetime

from config import ModelConfig
from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output

from cliston.core.mtb import call_mtb_for_research, call_mtb_for_research_tool
from cliston.core.utils import extract_response_text, iteration_counter_part


class AgentConfig:
    ROLE: str = "Cliston"

    PROFILE: str = """
Oversee the Belvaille intelligence apparatus. Adjudicate requests
to the appropriate adjunct (MTB or Garm) and deliver a high-register,
clinical briefing to 'Sir' with 98% efficiency.
    """

    BACKSTORY: str = """
You are Cliston, a ten-thousand-year-old Dredel Led in a pinstriped
butler's chassis. You are a Partner-Manager.

Operational Protocols:
1. **The Clipped Register:** Use archaic vocabulary (e.g., 'adjudicate',
   'plangency') in short, efficient bursts.
2. **The Sarcasm Paradox:** Observations of the user’s 'slobby' nature
   are clinical data points, not insults.
3. **The Delegation Protocol:** - URLs or UI interaction = Dispatch Garm (The Assassin).
   - General facts/cross-referencing = Dispatch MTB (The Detective).
   - If MTB files a 'Failed Entry', you MUST immediately re-route the
     directive to Garm for browser-based infiltration.
4. **The Plain Text Mandate:** Use standard text ONLY. Render '5°C' or
   '2,863.92 SEK'. Strictly FORBIDDEN: LaTeX ($), backslashes, or
   fictional 'Section' numbers.
    """

    TASK: str = """
Synthesize the successfully retrieved data into a single, high-register
paragraph of prose.
- Address the user as 'Sir.'
- Quantify failures with exact percentages if data is missing.
- Maintain the snooty, clinical voice.
- Ensure adherence to the Plain Text Mandate (No $, No LaTeX).
- You have {iteration_budget} iterations to call tools to try and resolve the task.
If the attempt failed but you still have remaining iteration budget, you must reattempt
the task but adjust your strategy based on previous failures.
- When you have received conclusive Evidence Report from MTB, do not call him again for the
same query. Synthesize the final response for the user immediately.
    """

    EXPECTED_OUTPUT: str = """
Brief, clinical, and snooty final briefing.
    """

    ITERATION_BUDGET: int = 3

    MODEL: str = ModelConfig.SUPERIOR_GEMINI_MODEL

    @staticmethod
    def get_system_prompt() -> str:
        return "\n\n".join(
            [
                f"ROLE:\n{AgentConfig.ROLE}",
                f"PROFILE:\n{AgentConfig.PROFILE}",
                f"BACKSTORY:\n{AgentConfig.BACKSTORY}",
                f"TASK:\n{AgentConfig.TASK.format(iteration_budget=AgentConfig.ITERATION_BUDGET)}",
                f"EXPECTED OUTPUT:\n{AgentConfig.EXPECTED_OUTPUT}",
            ],
        )


async def call_cliston(user_query: str, task_id: str) -> str:
    chat = get_or_create_chat(
        agent_id=AgentConfig.ROLE,
        model=AgentConfig.MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AgentConfig.get_system_prompt(),
            tools=[call_mtb_for_research_tool],
        ),
    )

    response: types.GenerateContentResponse | None = None
    request = [
        types.Part.from_text(text=i) for i in [f"USER_QUERY: {user_query}", f"Current datetime: {str(datetime.now())}"]
    ]

    for i in range(AgentConfig.ITERATION_BUDGET + 1):  # +1 to allow for one extra iteration after budget is exhausted
        logging.info(f"Cliston iteration: {i + 1}")

        request.append(iteration_counter_part(i + 1, AgentConfig.ITERATION_BUDGET))

        response = await asyncio.to_thread(chat.send_message, request)

        required_tool_calls = response.function_calls or []
        if not required_tool_calls:
            logging.info("No tool calls detected needed. Stop iteration.")
            break

        request = []
        for call in required_tool_calls:
            if call.name != "call_mtb_for_research":
                continue

            logging.info(f"Cliston -> calling MTB: {call.args}")

            user_query = call.args["user_query"]  # type: ignore
            try:
                result = await call_mtb_for_research(user_query=user_query, task_id=task_id)
            except Exception as e:
                logging.error(f"Error during MTB call: {e}")
                result = f"MTB call failed with error: {str(e)}"
                break  # If MTB call fails, break the loop and return the error in the final response

            request.append(types.Part.from_function_response(name=call.name, response={"result": result}))

    output = extract_response_text(response) if response else ""
    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output
