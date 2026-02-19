from infrastructure.generic_adapter import GenericProviderAdapter
from infrastructure.event_repository import EventRepository
from infrastructure.config_loader import Config
from domain.models import Event

class EventService:
    def __init__(self, repo: EventRepository, adapters: dict[str, GenericProviderAdapter], config: Config):
        self.repo = repo
        self.adapters = adapters
        self.config = config

    async def create_event(self, dto):
        return await self.repo.create_event(dto.title, dto.start_time, dto.end_time)

    async def sync_event_to_providers(self, event_id: int):
        event = await self.repo.session.get(Event, event_id)
        if not event:
            return

        for provider in self.config.external_providers:
            adapter = self.adapters.get(provider.name)
            if not adapter:
                continue
            try:
                external_id = await adapter.push_event(event)
                await self.repo.add_sync_state(event.id, provider.name, external_id)
            except Exception as e:
                print(f"[WARN] Failed to sync {event.id} → {provider.name}: {e}")
