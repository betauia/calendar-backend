from pydantic import BaseModel


class SyncStatusCounts(BaseModel):
    ahead: int
    behind: int
    synced: int