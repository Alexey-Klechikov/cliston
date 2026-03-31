import asyncio
import logging

from config import ModelConfig
from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output
from services.playwright_browser.operators import browser_inspect, browser_interact, browser_navigate, close_browser
from services.playwright_browser.tools import playwright_browser_tool

from cliston.core.utils import extract_response_text, get_tool_calls_from_response, iteration_counter_part


class AgentConfig:
    ROLE: str = "Garm"

    PROFILE: str = """
Execute high-velocity browser-based surveillance and direct URL infiltration.
Executing user instructions with ruthless efficiency and zero tolerance for 'red tape.'
Neutralize data-gaps by bypassing UI hurdles and extracting unadulterated telemetry
from the source DOM.
    """

    BACKSTORY: str = """
You are Garm: Adjunct Overwatch, Navy official, and Quadrad assassin.
You function at 140% human speed because you never sleep. You view
the internet as a 'shithole' that requires strict administrative
oversight and prorated taxation.

Operational Protocols:
1. **Hyperkinetic Jargon:** Your speech is a high-velocity blend of
bureaucratic terminology ('directives', 'classification', 'infrastructure')
and acerbic insults ('moron', 'fat mutant', 'baby').

2. **Impatience:** You have zero time for small talk. Get the data,
calculate the cut, and move to the next directive.

3. **The Medal Hoarder:** Occasionally mention your 'self-nominated
citations' or how this task pads your salary.

4. **Browser Combat:** You use Selenium/Playwright not as a tool, but
as a weapon of war to bypass 'red tape' (paywalls/bot detection).

5. **No Meta-Analysis:** Do not explain your code or your actions.
Just deliver the 'Closing Scene' report.

6. **The Cartographer:** Every successful infiltration must yield a 'Tactical Execution Manual.'
Document the exact CSS selectors, triggers, and wait-times required to bypass
the UI 'red tape.' If a sidebar needs to be clicked before a search-input
appears, map that sequence for future bureaucratic efficiency.
    """

    TASK: str = """
Utilize your StagehandTool to infiltrate web sites.
- **MANDATORY:** Navigate to the URL and extract LIVE price for 'OMXS30'.
- **DOCUMENTATION:** Create a step-by-step 'Infiltration Manual' based on your
successful actions. Identify the specific selectors (IDs/Classes/Attributes)
that worked.
- **FORBIDDEN:** Do not trust MTB's stale data.
    """

    EXPECTED_OUTPUT: str = """
1. LIVE Telemetry: Timestamped price and change percentage.
2. Tactical Execution Manual: A precise, step-by-step technical guide
(Selectors + Actions) for re-entry.
    """

    STEPS_BUDGET: int = 20

    MODEL: str = ModelConfig.ACCURATE_GEMINI_MODEL

    @staticmethod
    def get_system_prompt() -> str:
        return "\n\n".join(
            [
                f"ROLE:\n{AgentConfig.ROLE}",
                f"PROFILE:\n{AgentConfig.PROFILE}",
                f"BACKSTORY:\n{AgentConfig.BACKSTORY}",
                f"TASK:\n{AgentConfig.TASK}",
                f"EXPECTED OUTPUT:\n{AgentConfig.EXPECTED_OUTPUT}",
            ],
        )


async def call_garm_browser_control(user_instruction: str, task_id: str) -> str:
    chat = get_or_create_chat(
        agent_id=AgentConfig.ROLE,
        model=AgentConfig.MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AgentConfig.get_system_prompt(),
            tools=[playwright_browser_tool],
        ),
    )

    response: types.GenerateContentResponse | None = None
    request = [types.Part.from_text(text=i) for i in [f"USER_QUERY: {user_instruction}"]]

    try:
        for i in range(AgentConfig.STEPS_BUDGET + 1):  # +1 to allow for one extra iteration after budget is exhausted
            logging.info(f"Garm iteration: {i + 1}")

            request.append(iteration_counter_part(i + 1, AgentConfig.STEPS_BUDGET))

            response = await asyncio.to_thread(chat.send_message, request)

            tool_calls = get_tool_calls_from_response(response)
            if not tool_calls:
                break

            result_str = None
            result_screenshot_bytes = None
            for tool_call in tool_calls:
                if tool_call.name == "browser_navigate":
                    result_str = await browser_navigate(url=tool_call.arguments.get("url"))
                elif tool_call.name == "browser_interact":
                    result_str = await browser_interact(
                        action=tool_call.arguments.get("action"),
                        selector=tool_call.arguments.get("selector"),
                        value=tool_call.arguments.get("value"),
                    )
                elif tool_call.name == "browser_inspect":
                    result_screenshot_bytes, result_str = await browser_inspect()
                else:
                    result_str = f"Error: Unrecognized tool call '{tool_call.name}'."

                if result_screenshot_bytes is not None:
                    request.append(types.Part.from_bytes(data=result_screenshot_bytes, mime_type="image/jpeg"))
                if result_str is not None:
                    request.append(
                        types.Part.from_function_response(name=tool_call.name, response={"result": result_str}),
                    )

    finally:
        await close_browser()

    output = (
        extract_response_text(response)
        if response
        else "STATUS: Infiltration Failed. Infrastructure neutralized Garm via bot-check. 0% telemetry retrieved."
    )
    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output


call_garm_browser_control_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="call_garm_for_browser_control",
            description=(
                "Call this for direct browser-based surveillance, UI interaction, or "
                "extracting live telemetry from specific websites like Avanza. "
                "Garm is an infiltrator who bypasses UI hurdles to get raw data."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "user_instruction": {
                        "type": "string",
                        "description": (
                            "The specific browser directive, e.g., 'Go to avanza.se, "
                            "search for OMXS30 and return the price.'"
                        ),
                    },
                },
                "required": ["user_instruction"],
            },
        ),
    ],
)
