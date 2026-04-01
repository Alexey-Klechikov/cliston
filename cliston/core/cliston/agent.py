import asyncio
import logging
from datetime import datetime

from google.genai import types
from services.genai.operators import get_or_create_chat
from services.logging.operators import log_task_output

from cliston.core.cliston.config import AgentConfig
from cliston.core.garm.agent import call_garm_browser_control
from cliston.core.garm.tools import call_garm_browser_control_tool
from cliston.core.models import ToolCall
from cliston.core.mtb.agent import call_mtb_for_research
from cliston.core.mtb.tools import call_mtb_for_research_tool
from cliston.core.utils import extract_response_text, get_tool_calls_from_response, iteration_counter_part


async def _process_tools_calls(
    request: list[types.Part],
    tool_calls: list[ToolCall],
    task_id: str,
) -> list[types.Part]:
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
                    domain=tool_call.arguments.get("domain", ""),
                    objective=tool_call.arguments.get("objective", ""),
                    task_id=task_id,
                )
            except Exception as e:
                logging.error(f"Garm call failed: {e}")
                result = f"Garm call failed with error: {str(e)}"

        else:
            logging.error(f"Unrecognized tool call: {tool_call.name}")
            result = f"Error: Unrecognized tool call '{tool_call.name}'."

        request.append(types.Part.from_function_response(name=tool_call.name, response={"result": result}))

    return request


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
    request.append(iteration_counter_part(1, AgentConfig.ITERATION_BUDGET))

    for i in range(AgentConfig.ITERATION_BUDGET + 2):
        logging.info(f"Cliston iteration: {i + 1}")

        response = await asyncio.to_thread(chat.send_message, request)

        tool_calls = get_tool_calls_from_response(response)
        if not tool_calls:
            break

        request = [iteration_counter_part(i + 2, AgentConfig.ITERATION_BUDGET)]
        request = await _process_tools_calls(request, tool_calls, task_id)

    output = extract_response_text(response)

    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output
