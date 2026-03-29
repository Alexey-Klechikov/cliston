import logging

from core.models import ToolCall
from google.genai import types


def extract_response_text(response: types.GenerateContentResponse) -> str:
    candidates = response.candidates or []
    text_parts: list[str] = []

    for candidate in candidates:
        content = candidate.content
        if content is None:
            continue
        for part in content.parts or []:
            text = part.text
            if isinstance(text, str) and text:
                text_parts.append(text)

    return "\n".join(text_parts).strip()


def get_tool_calls_from_response(response: types.GenerateContentResponse) -> list[ToolCall]:
    function_calls: list[ToolCall] = []
    function_calls_candidates = response.function_calls or []

    if not function_calls_candidates:
        logging.info("No tool calls needed")
        return function_calls

    for candidate in function_calls_candidates:
        function_calls.append(ToolCall(name=candidate.name or "", arguments=candidate.args or {}))

    return function_calls


def iteration_counter_part(i: int, total: int) -> types.Part:
    text = f"ITERATION_COUNT: {i} / {total}"
    if i < total:
        pass
    else:
        text += " (final iteration, no more tool calls allowed)"

    return types.Part.from_text(text=text)
