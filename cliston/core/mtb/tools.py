from google.genai import types

call_mtb_for_research_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="call_mtb_for_research",
            description=(
                "Call this when you need deep web research, factual verification, "
                "or real-time data. MTB is a thorough investigator who returns evidence reports."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "The specific research question or topic for MTB to investigate.",
                    },
                },
                "required": ["user_query"],
            },
        ),
    ],
)
