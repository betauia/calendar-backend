from sqlalchemy import select
from domain.models import SyncState
from infrastructure.session import AsyncSessionLocal

class SyncStateRepository:
    async def get_all(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SyncState))
            return result.scalars().all()