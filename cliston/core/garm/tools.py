from google.genai import types

call_garm_browser_control_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="call_garm_for_browser_control",
            description=(
                "Call this for direct browser-based surveillance, UI interaction, or "
                "extracting live telemetry from specific websites like Avanza. "
                "Garm is an infiltrator who bypasses UI hurdles to get raw data."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The website domain to infiltrate, e.g., 'avanza.se'",
                    },
                    "tactical_manual_name": {
                        "type": "string",
                        "description": (
                            "Pass this to specify particular tactics for Garm. Either she extracts an "
                            "existing manual to replay, or she creates a new one with this specific name. "
                            "This is useful for complex interactions that require multiple steps, like "
                            "navigating a website to find specific information."
                        ),
                    },
                    "objective": {
                        "type": "string",
                        "description": (
                            "The specific data or interaction needed, e.g., 'Extract the live price of (e.g. OMXS30)'"
                        ),
                    },
                },
                "required": ["domain", "tactical_manual_name", "objective"],
            },
        ),
    ],
)
