# Cliston AI Assistant Implementation Plan

## Overview
Cliston is a personal AI assistant running on a Mac Mini, designed to:
- Converse in the style of a favorite book character
- Communicate via Telegram
- Browse the internet to answer questions
- Run efficiently on low-cost, low-RAM hardware (8GB Mac Mini)
- Be containerized for portability, with optimal use of Mac hardware

---

## Architecture

### 1. Ollama (LLM Host)
- Runs natively on macOS for GPU/Metal acceleration
- Hosts a quantized LLM (e.g., Llama 3.2 3B, Qwen 2.5 3B, Phi-3.5 Mini, or Gemma 2 2B)
- Custom character prompt via Modelfile

### 2. FastAPI Service (Dockerized)
- FastAPI acts as the backend for Cliston, exposing endpoints for Telegram webhooks and internal logic
- Contains:
   - CrewAI (agentic framework for character persona and tool use)
   - Web search tool (e.g., duckduckgo-search)
   - Logic to communicate with Ollama and process user messages
- Connects to Ollama via `http://host.docker.internal:11434`
- Handles all business logic, message routing, and web search

### 3. Telegram Bot Integration (via Webhook)
- Telegram bot is configured to use a webhook URL pointing to the FastAPI service
- When a message is sent to the bot, Telegram pings the FastAPI endpoint (e.g., `/webhook`)
- FastAPI processes the message, queries the AI, and responds to Telegram

### 4. Public Access via Tailscale Funnel
- Tailscale Funnel is used to securely expose the FastAPI webhook endpoint to the internet with HTTPS
- Telegram can reach the FastAPI service running on the Mac Mini without opening public ports or using ngrok

### 5. Internet Browsing
- CrewAI agent is equipped with a web search tool
- Uses DuckDuckGo or similar for search
- Integrates search results into character responses

---

## Implementation Steps


1. **Ollama Setup**
   - Install Ollama on Mac Mini
   - Download and run a suitable model (e.g., `ollama run qwen2.5:3b`)
   - Create a Modelfile for character persona

2. **Telegram Bot Setup**
   - Register a bot with @BotFather
   - Obtain API token

3. **FastAPI Service (Dockerized)**
   - Write FastAPI code to:
     - Expose a `/webhook` endpoint for Telegram
     - Process incoming Telegram messages
     - Forward messages to CrewAI agent and web search tool
     - Communicate with Ollama for character responses
     - Relay responses back to Telegram using Telegram API
   - Dockerize the service (use python:3.11-slim)
   - Use `host.docker.internal` to connect to Ollama

4. **Web Search Tool Integration**
   - Integrate duckduckgo-search or similar Python library
   - Register as a CrewAI tool

5. **Tailscale Funnel Setup**
   - Set up Tailscale and enable Funnel to expose FastAPI's webhook endpoint securely with HTTPS
   - Obtain the public HTTPS URL for Telegram webhook

6. **Telegram Webhook Configuration**
   - Set Telegram bot webhook to the Tailscale Funnel HTTPS URL (e.g., `https://<tailscale-funnel-url>/webhook`)

7. **Docker Compose**
   - Compose file to run the FastAPI service
   - Ollama runs natively (not in Docker)
   - Set environment variables for configuration

8. **Persistence (Optional)**
   - Mount Docker volume for logs or memory

---

## Key Files to Implement
- `Modelfile` (for Ollama character prompt)
- `Dockerfile` (for FastAPI/CrewAI/web search service)
- `docker-compose.yml` (to orchestrate services)
- `main.py` or `app.py` (FastAPI entrypoint)
- `requirements.txt` (Python dependencies)
- `config.py` (configuration management)

---

## Considerations
- Monitor RAM usage; use smallest model that meets needs
- Use Docker Desktop's Resource Saver mode if available
- Secure Telegram token and sensitive data
- Ensure outbound internet access for web search
- Optionally, add persistent storage for bot memory/logs
- FastAPI must be accessible via HTTPS for Telegram webhooks (Tailscale Funnel recommended for secure, zero-config HTTPS exposure)
- Telegram webhook must be set to the public URL provided by Tailscale Funnel
- Consider fallback to polling mode for development or if public exposure is not possible

---

## Next Steps
1. Choose and download LLM model for Ollama
2. Write Modelfile for character
3. Set up Telegram bot and obtain token
4. Scaffold Python service and Dockerfile
5. Integrate CrewAI and web search tool
6. Test end-to-end flow
7. Optimize for RAM and performance
