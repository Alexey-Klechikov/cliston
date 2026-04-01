import asyncio
import json
import logging

from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output
from services.playwright.operators import browser_inspect, browser_interact, browser_navigate, close_browser
from services.playwright.tools import playwright_browser_tool

from cliston.core.garm.config import AgentConfig
from cliston.core.garm.models import TacticalManual, ToolCallTrace
from cliston.core.garm.tactics_manager import TacticsManager
from cliston.core.models import ToolCall
from cliston.core.utils import extract_response_text, get_tool_calls_from_response, iteration_counter_part

CLOSING_SCENE_PROMPT = (
    "MISSION COMPLETE. Execute Protocol 'Closing Scene'. Format the telemetry and tactical manual into the "
    "required JSON structure immediately. Keep all data intact (specifically tool calls descriptions, values, "
    "and metadata). No further commentary."
)

REPLAY_VALIDATION_PROMPT = (
    "MANUAL REPLAY VALIDATION: Review the latest browser inspection result and determine whether the objective is "
    "already satisfied. If satisfied, return final response without additional tool calls. If not satisfied, restart "
    "autonomous planning from HOMEPAGE_URL. When restarting, the first tool call must be browser_navigate to "
    "HOMEPAGE_URL before any other tool call."
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


def _inject_manuals_with_iteration(
    request: list[types.Part],
    tactics_manager: TacticsManager,
    existing_manuals: list,
) -> list[types.Part]:
    request = tactics_manager.inject_manuals_into_request(request, existing_manuals)
    request.append(iteration_counter_part(1, AgentConfig.STEPS_BUDGET))
    return request


def _extract_report_json(report: types.GenerateContentResponse) -> dict:
    report_text = report.candidates[0].content.parts[0].text  # type: ignore[index]
    if not report_text:
        return {}
    return json.loads(report_text)


def _build_homepage_url(domain: str) -> str:
    normalized_domain = domain.strip()
    for prefix in ("http://", "https://", "www."):
        if not normalized_domain.startswith(prefix):
            continue
        normalized_domain = normalized_domain[len(prefix) :]
    return normalized_domain


async def _execute_replay_manual(
    request: list[types.Part],
    replay_manual: TacticalManual | None,
    objective: str,
    tactics_manager: TacticsManager,
    existing_manuals: list[TacticalManual],
    domain: str,
) -> list[types.Part]:
    if replay_manual:
        replay_tool_calls = tactics_manager.parse_manual_to_tool_calls(replay_manual.manual, objective)
        if replay_tool_calls:
            logging.info(
                "Replaying Tactical Manual '%s' with %s steps before autonomous planning.",
                replay_manual.objective,
                len(replay_tool_calls),
            )
            request.append(types.Part.from_text(text=f"REPLAYING_TACTICAL_MANUAL: {replay_manual.objective}"))
            request.append(iteration_counter_part(1, AgentConfig.STEPS_BUDGET))
            request = await _process_tools_calls(request, replay_tool_calls, tactics_manager)

            # Inspect state after replay so Garm can decide whether to finish or restart from homepage.
            request = await _process_tools_calls(
                request,
                [ToolCall(name="browser_inspect", arguments={})],
                tactics_manager,
            )
            request.append(types.Part.from_text(text=f"HOMEPAGE_URL: {domain}"))
            request.append(types.Part.from_text(text=REPLAY_VALIDATION_PROMPT))
        else:
            logging.warning(
                "Selected Tactical Manual '%s' could not be parsed into tool calls. "
                "Falling back to autonomous planning.",
                replay_manual.objective,
            )
            request = _inject_manuals_with_iteration(request, tactics_manager, existing_manuals)
            replay_manual = None
    else:
        request = _inject_manuals_with_iteration(request, tactics_manager, existing_manuals)

    return request


async def _process_tools_calls(
    request: list[types.Part],
    tool_calls: list[ToolCall],
    tactics_manager: TacticsManager,
) -> list[types.Part]:
    for tool_call in tool_calls:
        result_str, result_screenshot_bytes = await _execute_tool_call(tool_call)

        tactics_manager.execution_trace.append(
            ToolCallTrace(
                tool_call=tool_call,
                result=result_str,
            ),
        )

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
        is_single_use=True,  # chat is recreated every time
    )

    domain = _build_homepage_url(domain)

    response: types.GenerateContentResponse | None = None
    request = [types.Part.from_text(text=i) for i in [f"DOMAIN: {domain}", f"OBJECTIVE: {objective}"]]

    tactics_manager = TacticsManager()
    existing_manuals = await tactics_manager.tactics_storage.get_manuals(domain)
    replay_manual = tactics_manager.select_best_manual(existing_manuals, objective)

    request = await _execute_replay_manual(
        request=request,
        replay_manual=replay_manual,
        objective=objective,
        tactics_manager=tactics_manager,
        existing_manuals=existing_manuals,
        domain=domain,
    )

    try:
        for i in range(AgentConfig.STEPS_BUDGET + 2):
            logging.info(f"Garm iteration: {i + 1}")

            await asyncio.sleep(1)
            response = await asyncio.to_thread(chat.send_message, request)

            tool_calls = get_tool_calls_from_response(response)
            if not tool_calls:
                break

            request = [iteration_counter_part(i + 2, AgentConfig.STEPS_BUDGET)]
            request = await _process_tools_calls(request, tool_calls, tactics_manager)

    finally:
        await close_browser()

    if not response:
        logging.error("No response received from Garm after browser control operations.")
        return "Failure: No response received from Garm."

    report = await asyncio.to_thread(
        chat.send_message,
        CLOSING_SCENE_PROMPT,
        types.GenerateContentConfig(response_mime_type="application/json", response_schema=AgentConfig.REPORT_SCHEMA),
    )
    report_json = _extract_report_json(report)
    await tactics_manager.create_or_update_tactical_manual(
        domain=domain,
        objective=objective,
        report=report_json,
        existing_manuals=existing_manuals,
        replay_manual=replay_manual,
    )

    output = extract_response_text(response)

    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output
