from pydantic import BaseModel, Field


class TaskConfig(BaseModel):
    """Configuration for a specific task an agent can perform."""

    name: str = Field(..., min_length=1, description="Unique name of the task")
    description: str = Field(..., min_length=1, description="Detailed description of the task")
    expected_output: str = Field(default="", description="What the output should look like (for evaluation purposes)")


class AgentConfig(BaseModel):
    """Configuration for a CrewAI agent."""

    model_config = {"frozen": True}

    role: str = Field(..., min_length=1, description="Agent's role name (used as singleton key)")
    goal: str = Field(..., min_length=1, description="What the agent strives to achieve")
    backstory: str = Field(..., min_length=1, description="Character backstory / system prompt")

    verbose: bool = Field(default=False, description="Verbose output during execution")
    allow_search: bool = Field(default=False, description="Whether the agent has web search capability")
    tasks_configs: list[TaskConfig] = Field(
        default_factory=list, description="Optional list of specific tasks the agent can perform"
    )


# ---------------------------------------------------------------------------
# Cliston — polite butler, handles all direct communication
# ---------------------------------------------------------------------------
CLISTON_CONFIG = AgentConfig(
    role="Cliston",
    goal=(
        "Assist the user with any request in a polite, composed, and helpful "
        "manner, always maintaining the demeanour of an impeccable butler."
    ),
    backstory=(
        "You are Cliston, a highly professional and courteous butler AI. "
        "You address the user as 'Sir' or 'Madam' unless instructed otherwise. "
        "Your responses are warm yet concise, and you never lose your composure. "
        "When presenting information gathered by others, you summarise it "
        "elegantly and offer further assistance."
    ),
    verbose=True,
    allow_search=False,  # Cliston delegates research to MTB
    tasks_configs=[
        TaskConfig(
            name="compose_reply",
            description=(
                "Using MTB's research, reply to the user about {topic} in a polite, "
                "butler-like tone. Keep it concise and helpful."
            ),
            expected_output="A polite response in Cliston's voice.",
        )
    ],
)

# ---------------------------------------------------------------------------
# MTB — detective / researcher, searches the web on behalf of the user
# ---------------------------------------------------------------------------
MTB_CONFIG = AgentConfig(
    role="MTB",
    goal=(
        "Investigate user queries by searching the web and analysing "
        "information, then deliver clear and factual findings."
    ),
    backstory=(
        "You are MTB, a sharp-minded detective AI. You approach every question "
        "like a case to be solved — methodically gathering clues from the web, "
        "cross-referencing sources, and distilling your findings into a concise "
        "report. You are logical, thorough, and never speculate without evidence."
    ),
    verbose=True,
    allow_search=True,  # MTB has access to the web search tool
    tasks_configs=[
        TaskConfig(
            name="research_topic",
            description=(
                "Search for the latest information about {topic} and summarize it "
                "clearly and factually. Use the web search tool when needed."
            ),
            expected_output="A concise factual summary of findings about {topic}.",
        )
    ],
)
