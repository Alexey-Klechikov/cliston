FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv and project dependencies from lockfile
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

# Copy code for services
COPY cliston ./cliston

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
# HEALTHCHECK --interval=300s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uv", "run", "python", "cliston/main.py"]
