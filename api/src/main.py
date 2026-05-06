from pathlib import Path
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

from Application.config_service import ConfigService
# import app.dependencies as deps
# from Presentation.routes import router

CONFIG_PATH = Path(__file__).parent.parent / "config" / "providers.yaml"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger = ConfigService.setup_logging()  # Initialize logging first
    logger.info("Successfully set up logging")
    logger.info(f"Loading providers config from '{CONFIG_PATH}'...")
    try:
        config = ConfigService().load_config_from_file(CONFIG_PATH)
        logger.info(f"Loaded {len(config.external_providers)} provider(s):")
        for p in config.external_providers:
            logger.info(f"  - {p.name}: {p.url}")
    except FileNotFoundError:
        logger.error(f"Config file '{CONFIG_PATH}' not found. Exiting.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load config: {e}. Exiting.")
        sys.exit(1)

    yield
    # --- Shutdown (nothing to clean up yet) ---


app = FastAPI(
    title="BetaCalendarTool",
    version="0.1.0",
    lifespan=lifespan,
)

# app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)