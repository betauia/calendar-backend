from fastapi import APIRouter, BackgroundTasks
from domain.DTO.EventCreateDTO import EventCreateDTO
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.session import SessionLocal
from infrastructure.event_repository import EventRepository
from application.event_service import EventService
from infrastructure.config_loader import Config
from infrastructure.generic_adapter import GenericProviderAdapter  # <-- new

router = APIRouter()

# Load config and instantiate adapters dynamically
config = Config.load()
adapters = {p.name: GenericProviderAdapter(p.url) for p in config.external_providers}

@router.post("/events")
async def create_event(dto: EventCreateDTO, background_tasks: BackgroundTasks):
     async with SessionLocal() as session:
        repo = EventRepository(session)
        service = EventService(repo, adapters, config)
        # persist event
        event = await service.create_event(dto)
        # start async propagation
        background_tasks.add_task(service.sync_event_to_providers, event.id)
        return {"status": "ok", "event_id": event.id}
