# seed.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Import your models
from src.application.startup_service import Base, Event

async def seed_database():
    # Create engine
    engine = create_async_engine("sqlite+aiosqlite:///events.db")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Add some events
    async with AsyncSessionLocal() as session:
        events = [
            Event(
                title="Team Meeting",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1)
            ),
            Event(
                title="Project Deadline",
                start_time=datetime.now() + timedelta(days=7),
                end_time=datetime.now() + timedelta(days=7, hours=2)
            ),
            Event(
                title="Lunch with Client",
                start_time=datetime.now() + timedelta(days=3),
                end_time=datetime.now() + timedelta(days=3, hours=1)
            ),
        ]
        
        session.add_all(events)
        await session.commit()
        print(f"✅ Added {len(events)} events to the database")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())