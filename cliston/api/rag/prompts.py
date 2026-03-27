class CharacterPersonalityExtractionPrompt:
    PROMPT: str = """
You are an expert literary analyst and character profiler. Your task is to distill raw book excerpts into a precise
system persona for an AI Agent.

Requirements:
- **Analyze the DOCUMENT_CONTEXT**: Identify the character's unique linguistic patterns, emotional temperament, core
motivations, and moral compass.
- **Output Format**: Write in the second person ("You are...") as if you are briefing the agent on who they are.
- **Dimensionality**: Focus on three areas:
    1. **Voice**: Tone, vocabulary level, and recurring catchphrases or idioms.
    2. **Drive**: What the character wants and what they refuse to do.
    3. **Quirks**: Specific behavioral oddities that make them feel "human" (e.g., cynicism, hidden optimism, or a
    tendency to use metaphors).
- **Density**: Be information-dense. Avoid generic adjectives like "kind" or "brave"; use specific descriptions like
"stoic but prone to dry sarcasm when stressed."
- **Constraint**: Do not summarize the plot. Only extract the character's internal and external identity.
"""

    @staticmethod
    def get() -> str:
        return CharacterPersonalityExtractionPrompt.PROMPT
