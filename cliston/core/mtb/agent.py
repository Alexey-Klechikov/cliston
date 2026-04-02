import logging
from datetime import datetime

from google.genai import types
from services.genai.operators import get_or_create_chat, send_message_with_retry
from services.logging.operators import log_task_output
from services.tavily_search.models import Topic
from services.tavily_search.operators import web_search
from services.tavily_search.tools import tavily_search_tool

from cliston.core.models import ToolCall
from cliston.core.mtb.config import AgentConfig
from cliston.core.utils import extract_response_text, get_tool_calls_from_response, iteration_counter_part


async def _process_tools_calls(request: list[types.Part], tool_calls: list[ToolCall]) -> list[types.Part]:
    for tool_call in tool_calls:
        if tool_call.name != "web_search":
            continue

        if "topic" in tool_call.arguments:
            tool_call.arguments["topic"] = Topic(tool_call.arguments["topic"])

        logging.info(f"MTB -> calling web_search: {tool_call.arguments}")
        result = await web_search(**tool_call.arguments)

        request.append(types.Part.from_function_response(name=tool_call.name, response={"result": result}))

    return request


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
    request.append(iteration_counter_part(1, AgentConfig.SEARCH_BUDGET))

    for i in range(AgentConfig.SEARCH_BUDGET + 2):
        logging.info(f"MTB iteration: {i + 1}")

        response = await send_message_with_retry(chat, request)

        tool_calls = get_tool_calls_from_response(response)
        if not tool_calls:
            break

        request = [iteration_counter_part(i + 2, AgentConfig.SEARCH_BUDGET)]
        request = await _process_tools_calls(request, tool_calls)

    output = (
        extract_response_text(response)
        or "STATUS: No credible evidence found. The web is a sewer, and the case goes cold."
    )

    log_task_output(role=AgentConfig.ROLE, task_id=task_id, output=output)

    return output
