from domain.models import Event, SyncState
from sqlalchemy.ext.asyncio import AsyncSession

class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(self, title, start_time, end_time) -> Event:
        event = Event(title=title, start_time=start_time, end_time=end_time)
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def add_sync_state(self, event_id: int, provider_name: str, external_event_id: str):
        state = SyncState(event_id=event_id, provider_name=provider_name, external_event_id=external_event_id)
        self.session.add(state)
        await self.session.commit()
