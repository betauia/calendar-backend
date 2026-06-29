# Infrastructure/ExternalEventMappingStore.py
import logging
from src.Domain.ExternalEventMapping import ExternalEventMapping
from src.Domain.ExternalProvider import ExternalProvider

logger = logging.getLogger(__name__)

class ExternalEventMappingStore:

    def __init__(self) -> None:
        self._mappings: dict[tuple[int, ExternalProvider], ExternalEventMapping] = {}

    def put(self, mapping: ExternalEventMapping) -> None:
        event_id = mapping.truth_event_id
        provider_name = mapping.provider
        
        key = (event_id, provider_name)
        exists = key in self._mappings
        self._mappings[key] = mapping
        if exists:
            logger.info(f"Updated mapping for event {event_id}")
        else:
            logger.info(f"Created mapping for event {event_id}")

    def get(self, event_id: int, provider: ExternalProvider) -> ExternalEventMapping | None:
        return self._mappings.get((event_id, provider), None)
