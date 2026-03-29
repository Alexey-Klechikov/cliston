from google.genai import types

tavily_search_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="web_search",
            description="Searches the internet for real-time information, news, and financial data.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string."},
                    "topic": {
                        "type": "string",
                        "enum": ["general", "news", "finance"],
                        "description": "The category of the search.",
                    },
                    "days": {"type": "integer", "description": "Number of days to look back for recent news/info."},
                },
                "required": ["query", "topic"],
            },
        ),
    ],
)
