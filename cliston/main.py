import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.health.routers import router as health_router

# Import routers
from api.task.routers import router as task_router
from config import AppConfig

# Configure logging
log_level = AppConfig.LOG_LEVEL
log_format = "%(asctime)s [%(levelname)s] %(message)s"
if log_level.upper() == "DEBUG":
    log_format = "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s"

logging.basicConfig(level=getattr(logging, log_level), format=log_format)

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    logging.info("Starting up Cliston...")

    yield

    # Shutdown
    logging.info("Shutting down Cliston...")


# Initialize FastAPI app
app = FastAPI(
    title=AppConfig.API_TITLE,
    version=AppConfig.API_VERSION,
    description="Cliston",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)
app.include_router(task_router)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(_, exc):
    logging.error(f"Uncaught exception: {exc}", exc_info=True)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Internal server error"})


def main():
    logging.info(f"Starting {AppConfig.API_TITLE} v{AppConfig.API_VERSION}")
    logging.info(f"Server will be available at http://{AppConfig.API_HOST}:{AppConfig.API_PORT}")
    logging.info(f"Docs available at http://{AppConfig.API_HOST}:{AppConfig.API_PORT}/docs")

    uvicorn.run(
        app,
        host=AppConfig.API_HOST,
        port=AppConfig.API_PORT,
        reload=False,
        log_level=AppConfig.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
