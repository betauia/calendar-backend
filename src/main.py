from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI

from Application.calendar_service_registry import CalendarServiceRegistry
from Application.config_service import ConfigService
from Application.sync_service import SyncService
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore
from Infrastructure.remote_calendar_service import RemoteCalendarService
from Infrastructure.truth_calendar_service import TruthCalendarService
from Presentation.routes import Routes

CONFIG_PATH = Path(__file__).parent.parent / "config" / "providers.yaml"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setting up logging and loading configuration
    _config_service = ConfigService()

    logger = _config_service.setup_logging()
    logger.info("Successfully set up logging")
    logger.info(f"Loading providers config from '{CONFIG_PATH}'...")

    # Loading providers from configuration file
    config = _config_service.load_config_from_file(CONFIG_PATH)
    logger.info(f"Loaded {len(config.external_providers)} provider(s):")
    for p in config.external_providers:
        logger.info(f"  - {p.name}: {p.url}")

    # Registering calendar services for each provider
    service_registry = CalendarServiceRegistry()
    for provider in config.external_providers:
        logger.info(f"Registering calendar service for provider '{provider.name}'...")
        service_registry.register(provider, RemoteCalendarService(provider))

    truth_service = TruthCalendarService()
    mapping_store = ExternalEventMappingStore()
    sync_service = SyncService(truth_service=truth_service, registry=service_registry, mapping_store=mapping_store)

    sync_status_all = sync_service.get_all_calendars_sync_status()
    
    print(f"Sync Status for all providers:", sync_status_all.model_dump(mode="json"))
    
    routes = Routes(sync_service=sync_service, providers=config)
    app.include_router(routes.router)

    logger.info("Startup complete. API is ready to accept requests.")

    yield


app = FastAPI(
    title="BetaCalendarTool",
    version="0.1.0",
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)