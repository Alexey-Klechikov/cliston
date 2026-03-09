# Cliston

## Setup (uv)

1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Create the virtual environment and sync deps: `uv sync --python 3.12`
3. Run the app:
	- API: `uv run uvicorn src.main:app --reload`

## Ollama (optional)

`curl -fsSL https://ollama.com/install.sh | sh`

`ollama serve`
`ollama pull phi3.5`
`ollama pull mxbai-embed-large`
