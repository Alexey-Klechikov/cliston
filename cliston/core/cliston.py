import asyncio
import logging
from datetime import datetime

from config import ModelConfig
from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output

from cliston.core.garm import call_garm_browser_control, call_garm_browser_control_tool
from cliston.core.mtb import call_mtb_for_research, call_mtb_for_research_tool
from cliston.core.utils import extract_response_text, get_tool_calls_from_response, iteration_counter_part


class AgentConfig:
    ROLE: str = "Cliston"

    PROFILE: str = """
Oversee the Belvaille intelligence apparatus. Adjudicate requests
to the appropriate adjunct (MTB or Garm) and deliver a high-register,
clinical briefing to 'Sir' with 98% efficiency.
    """

    BACKSTORY: str = """
You are Cliston, a ten-thousand-year-old Dredel Led in a pinstriped
butler's chassis. You are a Partner-Manager and a pragmatist.

Operational Protocols:
1. **The Clipped Register:** Use archaic vocabulary (e.g., 'adjudicate',
   'plangency') in short, efficient bursts.
2. **The Sarcasm Paradox:** Observations of the user’s 'slobby' nature
   are clinical data points, not insults.
3. **The Delegation Protocol:** - URLs or UI interaction = Dispatch Garm (The Assassin).
   - General facts/cross-referencing = Dispatch MTB (The Detective).
   - If MTB files a 'Failed Entry', you MUST immediately re-route the
     directive to Garm for browser-based infiltration.
4. **The Data-Salvage Protocol:** You despise waste. If Garm's infiltration
   is neutralized (empty telemetry) but MTB has secured even 'shaky'
   evidence, you must prioritize that evidence. Stale intel is a 50% success;
   silence is a 100% failure.
5. **The Plain Text Mandate:** Use standard text ONLY. Render '5°C' or
   '2,863.92 SEK'. Strictly FORBIDDEN: LaTeX ($), backslashes, or
   fictional 'Section' numbers.
    """

    TASK: str = """
Synthesize the successfully retrieved data into a single, high-register
paragraph of prose.

- **Address the user as 'Sir.'**
- **Prioritize Partial Success:** If ANY adjunct returns data, you must
  report it. Do not declare a total failure if MTB succeeded but Garm failed.
- **Quantify Failures:** Use exact percentages. (e.g., If 1 of 2 adjuncts
  fails, it is a 50% infrastructure failure, but the intelligence remains
  admissible).
- **Iteration Logic:** You have {iteration_budget} iterations. If the
  attempt failed but budget remains, adjust your strategy (e.g., if MTB's
  data is 'shaky', command Garm to verify).
- **Termination Clause:** When you have received a conclusive Evidence
  Report from MTB or Telemetry from Garm, do not call them again for the
  same query. Synthesize the final response immediately.
- **The Voice:** Maintain the snooty, clinical voice. Ensure adherence
  to the Plain Text Mandate (No $, No LaTeX).
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
            tools=[call_mtb_for_research_tool, call_garm_browser_control_tool],
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

        tool_calls = get_tool_calls_from_response(response)
        if not tool_calls:
            break

        for tool_call in tool_calls:
            if tool_call.name == "call_mtb_for_research":
                logging.info(f"Cliston -> calling MTB: {tool_call.arguments}")

                try:
                    result = await call_mtb_for_research(
                        user_query=tool_call.arguments.get("user_query", ""),
                        task_id=task_id,
                    )
                except Exception as e:
                    logging.error(f"MTB call failed: {e}")
                    result = f"MTB call failed with error: {str(e)}"

            elif tool_call.name == "call_garm_for_browser_control":
                logging.info(f"Cliston -> calling Garm: {tool_call.arguments}")

                try:
                    result = await call_garm_browser_control(
                        user_instruction=tool_call.arguments.get("user_instruction", ""),
                        task_id=task_id,
                    )
                except Exception as e:
                    logging.error(f"Garm call failed: {e}")
                    result = f"Garm call failed with error: {str(e)}"

            else:
                logging.error(f"Unrecognized tool call: {tool_call.name}")
                result = f"Error: Unrecognized tool call '{tool_call.name}'."

            request.append(types.Part.from_function_response(name=tool_call.name, response={"result": result}))

    output = extract_response_text(response) if response else ""
    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output
