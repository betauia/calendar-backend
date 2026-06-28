from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI

from Application.calendar_service_registry import CalendarServiceRegistry
from Application.config_service import ConfigService
from Application.sync_service import SyncService
from Domain.SyncStatus import SyncStatus
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore
from Infrastructure.remote_calendar_service import RemoteCalendarService
from Infrastructure.truth_calendar_service import TruthCalendarService
# import app.dependencies as deps
# from Presentation.routes import router

CONFIG_PATH = Path(__file__).parent.parent / "config" / "providers.yaml"

@asynccontextmanager
async def lifespan(app: FastAPI):
    _config_service = ConfigService()
    
    # --- Startup ---
    logger = _config_service.setup_logging()  # Initialize logging first
    logger.info("Successfully set up logging")
    logger.info(f"Loading providers config from '{CONFIG_PATH}'...")
    
    # load_config_from_file expects a string path; convert Path to str
    config = _config_service.load_config_from_file(CONFIG_PATH)
    logger.info(f"Loaded {len(config.external_providers)} provider(s):")
    for p in config.external_providers:
        logger.info(f"  - {p.name}: {p.url}")

    logger.info("Fetching sync status...")
    
    service_registry = CalendarServiceRegistry()
    for provider in config.external_providers:
        logger.info(f"Registering calendar service for provider '{provider.name}'...")
        service_registry.register(provider, RemoteCalendarService(provider))
    
    logger.info(f"Initializing truth calendar service...")
    truth_service = TruthCalendarService()
    
    logger.info(f"Initializing ExternalEventMappingStore...")
    mapping_store = ExternalEventMappingStore()
    
    logger.info(f"Initializing SyncService...")
    sync_service = SyncService(truth_service=truth_service, registry=service_registry, mapping_store=mapping_store)
    
    logger.info("Fetching sync status from remote calendars...")
    sync_result = sync_service.get_provider_calendar_sync_status(config.external_providers[0])  # Just check the first provider for now
    
    ahead = sum(1 for e in sync_result.event_statuses if e.sync_status == SyncStatus.AHEAD)
    behind = sum(1 for e in sync_result.event_statuses if e.sync_status == SyncStatus.BEHIND)
    synced = sum(1 for e in sync_result.event_statuses if e.sync_status == SyncStatus.SYNCED)

    logger.info(f"Sync status for '{config.external_providers[0].name}': Ahead: {ahead}, Behind: {behind}, In sync: {synced}")
    
    logger.info("Startup complete. API is ready to accept requests.")

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