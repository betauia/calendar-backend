from enum import Enum


class SyncStatus(Enum):
    SYNCED = "synced"
    AHEAD = "ahead"
    BEHIND = "behind"