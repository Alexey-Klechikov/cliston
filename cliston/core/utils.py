import logging

from google.genai import types

from cliston.core.models import ToolCall


def extract_response_text(response: types.GenerateContentResponse | None) -> str:
    if response is None:
        return ""

    candidates = response.candidates or []
    text_parts: list[str | dict] = []

    for candidate in candidates:
        content = candidate.content
        if content is None:
            continue
        for part in content.parts or []:
            text = part.text

            if not text:
                continue

            text_parts.append(text)

    return "\n".join(map(str, text_parts))


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
