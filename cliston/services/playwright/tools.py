from google.genai import types

playwright_browser_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="browser_navigate",
            description="Navigate to a specific URL and return the page summary.",
            parameters_json_schema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL to visit."}},
                "required": ["url"],
            },
        ),
        types.FunctionDeclaration(
            name="browser_interact",
            description=(
                "Perform an action like click, type, or keypress on the current page. "
                "For selector, prefer CSS from browser_inspect suggested_selector. "
                "Plain tokens like 'search-input' are also accepted and auto-resolved."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["click", "type", "keypress"]},
                    "selector": {"type": "string", "description": "The CSS selector or text of the element."},
                    "value": {"type": "string", "description": "The text to type (if action is 'type')."},
                },
                "required": ["action", "selector"],
            },
        ),
        types.FunctionDeclaration(
            name="browser_inspect",
            description="Use this to see the current page content, text, and structure after an action.",
            parameters_json_schema={"type": "object", "properties": {}},  # No args needed
        ),
    ],
)
