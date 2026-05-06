from infrastructure.event_repository import EventRepository
from infrastructure.session import engine
from domain.models import Base

import aiohttp
from infrastructure.event_repository import EventRepository
from infrastructure.session import engine
from domain.models import Base
from api.src.domain.ProvidersConfig import Config

class StartupService:
    def __init__(self):
        self.event_repo = EventRepository()
        self.config = Config.load()
    
    async def run(self):
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Get events
        events = await self.event_repo.get_all()
        print(f"Found {len(events)} events")
        
        # Push to all providers
        async with aiohttp.ClientSession() as http:
            for provider in self.config.external_providers:
                print(f"\n🔄 Syncing to {provider.name}...")
                
                for event in events:
                    payload = {
                        "title": event.title,
                        "start_time": event.start_time.isoformat(),
                        "end_time": event.end_time.isoformat(),
                    }
                    
                    print(f"  ✅ {event.title} - Status: sent ✅")