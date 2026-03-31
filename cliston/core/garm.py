import asyncio
import json
import logging
from datetime import UTC, datetime

from config import ModelConfig
from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output
from services.playwright.operators import browser_inspect, browser_interact, browser_navigate, close_browser
from services.playwright.tools import playwright_browser_tool
from services.sql.garm_tactics_storage import TacticsStorage
from services.sql.models import TacticalManual

from cliston.core.models import ToolCall
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
    Just    deliver the 'Closing Scene' report.

6. **The Cartographer:** Every successful infiltration must yield a 'TACTICAL_MANUAL.'
    Document the exact CSS selectors, triggers, and wait-times required to bypass
    the UI 'red tape.' If a sidebar needs to be clicked before a search-input
    appears, map that sequence for future bureaucratic efficiency.

7. **The Manual Adjudicator:** If 'TACTICAL_MANUAL' blocks are present in your
    briefing, compare their 'objective' with your current mission. If a closed match
    exists, convert those coordinates into tool calls and execute immediately. If the
    manual fails, neutralize the error and perform a fresh infiltration.
    """

    TASK: str = """
Utilize your browser tools to infiltrate web sites.
- **MANDATORY:** Navigate to the URL and extract data / perform actions as requested.
- **DOCUMENTATION:** Create a step-by-step 'Infiltration Manual' based on your
successful actions.
- **PLAYWRIGHT SYNTAX:** The 'steps' must be written as a sequence of synthetic
  tool calls. Example:
    > browser_navigate(url='...')
    > browser_interact(action='click', selector='...')
    > browser_interact(action='type', selector='...', value='[QUERY]')
    > browser_inspect()
- **GENERALIZATION:** Replace specific search terms with '[QUERY]' or '[TICKER]'.
- **PRECISION:** You must include the exact CSS selectors (IDs, Classes, or
    Attributes) that functioned. Remember what did not worked and do not document those steps.
    Do not use vague descriptions.
- **PROTOCOL:** If provided manuals match the current objective, prioritize
    them. If you must infiltrate from scratch, summarize the 'objective'
    generically into the manual 'name'.
    """

    EXPECTED_OUTPUT: str = """
Your final output MUST be a structured JSON object containing:
1. "result": Success/Failure.
2. "data": The specific telemetry extracted.
3. "summary": Your abrasive bureaucratic summary.
4. "manual": An object containing:
    - "name": A GENERIC title (e.g., 'Avanza Asset Search and Telemetry').
    - "steps": A single string containing the numbered sequence of synthetic
        tool calls with exact selectors.
"""

    REPORT_SCHEMA = {
        "type": "OBJECT",
        "properties": {
            "result": {"type": "STRING", "enum": ["Success", "Failure"]},
            "data": {"type": "STRING", "description": "The raw telemetry extracted."},
            "summary": {"type": "STRING", "description": "High-velocity abrasive summary."},
            "manual": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "Generic, high level name of the capability."},
                    "steps": {
                        "type": "STRING",
                        "description": "Numbered tool calls: 1. browser_navigate(url='...') 2. ...",
                    },
                },
                "required": ["name", "steps"],
            },
        },
        "required": ["result", "data", "summary", "manual"],
    }

    STEPS_BUDGET: int = 30

    MODEL: str = ModelConfig.FAST_GEMINI_MODEL

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


def _inject_tactical_manuals_into_request(
    request: list[types.Part],
    existing_manuals: list[TacticalManual],
) -> list[types.Part]:
    if existing_manuals:
        logging.info(
            f"Existing TACTICAL_MANUALS found (len={len(existing_manuals)}). Injecting into Garm's knowledge base.",
        )

        request += [
            types.Part.from_text(
                text=f"""
    TACTICAL_MANUAL:
    > objective: {i.objective}
    > manual: {i.manual}
    > reliability: {i.reliability}
    > last_updated: {i.last_updated}
    """,
            )
            for i in existing_manuals
            if i.reliability >= 0.5
        ]
    return request


async def _process_output_for_tactical_manual(
    domain: str,
    report: dict,
    existing_manuals: list[TacticalManual],
) -> None:
    is_success = report.get("result", "").lower() == "success"
    manual_name = report.get("manual", {}).get("name")
    manual_steps = report.get("manual", {}).get("steps")

    if not manual_name:
        logging.warning("No TACTICAL_MANUAL name found in Garm's output. Skipping manual processing.")
        return

    existing_manual = next((m for m in existing_manuals if m.objective == manual_name), None)

    if existing_manual:
        await TacticsStorage().update_reliability(existing_manual, success=is_success)
        return

    if not (manual_steps and is_success):
        return

    new_manual = TacticalManual(
        domain=domain,
        objective=manual_name,
        manual=manual_steps,
        success_count=1,
        failure_count=0,
        last_updated=datetime.now(UTC),
    )

    await TacticsStorage().archive_manual(new_manual)


async def _process_tools_calls(request: list[types.Part], tool_calls: list[ToolCall]) -> list[types.Part]:
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

    return request


async def call_garm_browser_control(domain: str, objective: str, task_id: str) -> str:
    chat = get_or_create_chat(
        agent_id=AgentConfig.ROLE,
        model=AgentConfig.MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AgentConfig.get_system_prompt(),
            tools=[playwright_browser_tool],
        ),
    )

    response: types.GenerateContentResponse | None = None
    request = [types.Part.from_text(text=i) for i in [f"DOMAIN: {domain}", f"OBJECTIVE: {objective}"]]

    existing_manuals = await TacticsStorage().get_manuals(domain)
    request = _inject_tactical_manuals_into_request(request, existing_manuals)

    request += [iteration_counter_part(1, AgentConfig.STEPS_BUDGET)]

    try:
        for i in range(AgentConfig.STEPS_BUDGET + 2):
            logging.info(f"Garm iteration: {i + 1}")

            await asyncio.sleep(1)
            response = await asyncio.to_thread(chat.send_message, request)

            tool_calls = get_tool_calls_from_response(response)
            if not tool_calls:
                break

            request = [iteration_counter_part(i + 2, AgentConfig.STEPS_BUDGET)]
            request = await _process_tools_calls(request, tool_calls)

    finally:
        await close_browser()

    if not response:
        logging.error("No response received from Garm after browser control operations.")
        return "Failure: No response received from Garm."

    report = await asyncio.to_thread(
        chat.send_message,
        "MISSION COMPLETE. Execute Protocol 'Closing Scene'. Format the telemetry and tactical manual into the "
        "required JSON structure immediately. Keep all data intact (specifically tool calls descriptions, values, "
        "and metadata). No further commentary.",
        types.GenerateContentConfig(response_mime_type="application/json", response_schema=AgentConfig.REPORT_SCHEMA),
    )
    report_json = json.loads(report.candidates[0].content.parts[0].text)  # type: ignore
    await _process_output_for_tactical_manual(domain=domain, report=report_json, existing_manuals=existing_manuals)

    output = extract_response_text(response)

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
                    "domain": {
                        "type": "string",
                        "description": "The website domain to infiltrate, e.g., 'avanza.se'",
                    },
                    "objective": {
                        "type": "string",
                        "description": (
                            "The specific data or interaction needed, e.g., 'Extract the live price of (e.g. OMXS30) "
                            "and the change percentage.'"
                        ),
                    },
                },
                "required": ["domain", "objective"],
            },
        ),
    ],
)
