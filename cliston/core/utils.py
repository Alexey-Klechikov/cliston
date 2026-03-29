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


def iteration_counter_part(i: int, total: int) -> types.Part:
    text = f"ITERATION_COUNT: {i} / {total}"
    if i < total:
        pass
    else:
        text += " (final iteration, no more tool calls allowed)"

    return types.Part.from_text(text=text)
