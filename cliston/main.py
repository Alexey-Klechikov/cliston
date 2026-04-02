import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import routers
from api.health.routers import router as health_router
from api.rag.routers import router as rag_router
from api.task.routers import router as task_router

from cliston.settings import settings

# Configure logging
log_level = settings.LOG_LEVEL
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
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Cliston",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)
app.include_router(task_router)
app.include_router(rag_router)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(_, exc):
    logging.error(f"Uncaught exception: {exc}", exc_info=True)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Internal server error"})


@app.middleware("http")
async def catch_unhandled_exceptions(request: Request, call_next):
    try:
        logging.info("-" * 20)

        return await call_next(request)

    except HTTPException:
        raise

    except Exception as exc:
        logging.error("Unhandled request error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )


def main():
    logging.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logging.info(f"Server will be available at http://{settings.API_HOST}:{settings.API_PORT}")
    logging.info(f"Docs available at http://{settings.API_HOST}:{settings.API_PORT}/docs")

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
