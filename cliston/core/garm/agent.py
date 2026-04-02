import asyncio
import json
import logging

from google.genai import types
from services.genai.operators import get_or_create_chat, send_message_with_retry
from services.logging.operators import log_task_output
from services.playwright.operators import browser_inspect, browser_interact, browser_navigate, close_browser
from services.playwright.tools import playwright_browser_tool

from cliston.core.garm.config import AgentConfig
from cliston.core.garm.models import Report, ReportManual, ReportResult, TacticalManual, ToolCallTrace
from cliston.core.garm.tactics_manager import TacticsManager
from cliston.core.models import ToolCall
from cliston.core.utils import get_tool_calls_from_response, iteration_counter_part

TACTICAL_MANUAL_REPLAY_RESULT_PROMPT = (
    "Review the browser inspection result and determine whether it is sufficient to fulfill the "
    "objective: {objective}. "
    "If it does, format the telemetry into the required JSON structure immediately. "
    "If not satisfied, follow the same JSON structure for output, but indicate failure."
)
AUTONOMOUS_PLANNING_RESULT_PROMPT = (
    "MISSION COMPLETE. Execute Protocol 'Closing Scene'. Review the latest browser inspection result and determine "
    "whether the objective is satisfied. If satisfied, format the telemetry and tactical manual into the required "
    "JSON structure immediately. Keep all data intact (specifically tool calls descriptions, values, and metadata). "
    "No further commentary."
)


async def _execute_tool_call(tool_call: ToolCall) -> tuple[str, bytes | None]:
    if tool_call.name == "browser_navigate":
        result = await browser_navigate(url=tool_call.arguments.get("url"))
        return result or "", None

    if tool_call.name == "browser_interact":
        result = await browser_interact(
            action=tool_call.arguments.get("action"),
            selector=tool_call.arguments.get("selector"),
            value=tool_call.arguments.get("value"),
        )
        return result or "", None

    if tool_call.name == "browser_inspect":
        screenshot_bytes, result = await browser_inspect()
        return result or "", screenshot_bytes

    return f"Error: Unrecognized tool call '{tool_call.name}'.", None


def _extract_report_from_response(report: types.GenerateContentResponse) -> Report:
    report_text = report.candidates[0].content.parts[0].text  # type: ignore[index]
    if not report_text:
        return Report(result=ReportResult.FAILURE)
    return Report(**json.loads(report_text))


def _build_homepage_url(domain: str) -> str:
    normalized_domain = domain.strip().lower()
    for prefix in ("http://", "https://", "www."):
        normalized_domain = normalized_domain.replace(prefix, "")
    return normalized_domain


async def _execute_replay_tactical_manual(
    objective: str,
    tactical_manual: TacticalManual,
    tactics_manager: TacticsManager,
) -> Report:
    chat = get_or_create_chat(
        agent_id=AgentConfig.ROLE,
        model=AgentConfig.MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AgentConfig.get_system_prompt(),
            tools=[playwright_browser_tool],
        ),
        is_single_use=True,
    )

    replay_tool_calls = tactics_manager.parse_manual_to_tool_calls(
        tactical_manual,
        objective=objective,
    )
    if not replay_tool_calls:
        logging.info("Parsed replay manual has no tool calls, skipping replay.")
        return Report()

    logging.info(
        "Replaying Tactical Manual '%s' with %s steps before autonomous planning.",
        tactical_manual.objective,
        len(replay_tool_calls),
    )
    request = [types.Part.from_text(text=f"REPLAYING_TACTICAL_MANUAL: {tactical_manual.objective}")]

    result_str, result_screenshot_bytes = None, None
    try:
        for tool_call in replay_tool_calls + [ToolCall(name="browser_inspect", arguments={})]:
            await asyncio.sleep(1)  # brief pause to mimic human-like interaction and allow page to load
            logging.info(f"Replaying tool call: {tool_call}")
            result_str, result_screenshot_bytes = await _execute_tool_call(tool_call)
    finally:
        await close_browser()

    if result_screenshot_bytes is not None:
        request.append(types.Part.from_bytes(data=result_screenshot_bytes, mime_type="image/jpeg"))
    if result_str is not None:
        request.append(
            types.Part.from_function_response(name="FINAL_PAGE_CONTENT", response={"result": result_str}),
        )

    report_response = await send_message_with_retry(
        chat,
        request + [types.Part.from_text(text=TACTICAL_MANUAL_REPLAY_RESULT_PROMPT.format(objective=objective))],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AgentConfig.REPORT_SCHEMA,
        ),
    )
    report = _extract_report_from_response(report_response)
    report.manual = ReportManual(name=tactical_manual.objective, steps=tactical_manual.steps)

    return report


async def _execute_autonomous_planning(
    request: list[types.Part],
    tactics_manager: TacticsManager,
) -> Report:
    logging.info("No suitable manual to replay or replay failed validation. Starting autonomous planning.")
    chat = get_or_create_chat(
        agent_id=AgentConfig.ROLE,
        model=AgentConfig.MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AgentConfig.get_system_prompt(),
            tools=[playwright_browser_tool],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
        is_single_use=True,
    )
    try:
        for i in range(AgentConfig.STEPS_BUDGET + 2):
            logging.info(f"Garm iteration: {i + 1}")

            await asyncio.sleep(1)
            response = await send_message_with_retry(chat, request)

            tool_calls = get_tool_calls_from_response(response)
            if not tool_calls:
                break

            request = [iteration_counter_part(i + 2, AgentConfig.STEPS_BUDGET)]
            for tool_call in tool_calls:
                result_str, result_screenshot_bytes = await _execute_tool_call(tool_call)

                tactics_manager.execution_trace.append(ToolCallTrace(tool_call=tool_call, result=result_str))

                if result_screenshot_bytes is not None:
                    request.append(types.Part.from_bytes(data=result_screenshot_bytes, mime_type="image/jpeg"))
                if result_str is not None:
                    request.append(
                        types.Part.from_function_response(name=tool_call.name, response={"result": result_str}),
                    )

    finally:
        await close_browser()

    report_response = await send_message_with_retry(
        chat,
        AUTONOMOUS_PLANNING_RESULT_PROMPT,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AgentConfig.REPORT_SCHEMA,
        ),
    )
    report = _extract_report_from_response(report_response)

    return report


async def call_garm_browser_control(domain: str, objective: str, task_id: str) -> str:
    domain = _build_homepage_url(domain)

    initial_request = [types.Part.from_text(text=i) for i in [f"DOMAIN: {domain}", f"ORIGINAL_OBJECTIVE: {objective}"]]

    tactics_manager = TacticsManager()
    existing_manuals = await tactics_manager.tactics_storage.get_manuals(domain)
    tactical_manual = tactics_manager.select_best_manual(existing_manuals, objective)

    report = Report()
    if tactical_manual:
        report = await _execute_replay_tactical_manual(
            objective=objective,
            tactical_manual=tactical_manual,
            tactics_manager=tactics_manager,
        )
        await tactics_manager.create_or_update_tactical_manual(
            domain=domain,
            report=report,
            existing_manuals=existing_manuals,
        )

    if report.result == ReportResult.FAILURE:
        report = await _execute_autonomous_planning(
            request=initial_request.copy(),
            tactics_manager=tactics_manager,
        )

        await tactics_manager.create_or_update_tactical_manual(
            domain=domain,
            report=report,
            existing_manuals=existing_manuals,
        )

    if report.result == ReportResult.FAILURE and not report.summary:
        logging.error("All attempts failed. Returning failure report.")
        report.summary = "Failure: Both replay manual and autonomous planning failed."

    output = str(report.model_dump(mode="json", exclude_none=True))
    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output
