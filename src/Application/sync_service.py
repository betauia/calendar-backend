import logging

from Application.calendar_service_registry import CalendarServiceRegistry
from Application.i_remote_calendar_service import IRemoteCalendarService
from Application.models.result.calendar_sync_result import CalendarSyncResult
from Application.models.result.event_sync_result import EventSyncResult
from Application.models.result.sync_result import SyncResult
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.ExternalEventMapping import ExternalEventMapping
from Domain.RemoteCalendar import RemoteCalendar, RemoteCalendarEvent
from Domain.SyncStatus import SyncStatus
from Domain.ExternalProvider import ExternalProvider
from Domain.TruthCalendar import TruthCalendar, TruthCalendarEvent
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore
from Infrastructure.truth_calendar_service import TruthCalendarService

logger = logging.getLogger(__name__)

# This class does way too much
class SyncService:
    def __init__(
        self,
        truth_service: TruthCalendarService,
        registry: CalendarServiceRegistry,
        mapping_store: ExternalEventMappingStore,
    ) -> None:
        self._truth_service = truth_service
        self._registry = registry
        self._mapping_store = mapping_store

    def _get_truth_calendar(self) -> TruthCalendar:
        logger.debug("Fetching truth calendar events...")
        result = self._truth_service.get_calendar()
        if not result.is_successful or result.value is None:
            logger.error("Failed to fetch truth calendar events")
            raise Exception("Failed to fetch truth calendar events")
        logger.debug(f"Fetched {len(result.value.calendar_events)} events from truth calendar")
        return result.value

    def _get_provider_calendar(self, provider: ExternalProvider) -> RemoteCalendar:
        logger.debug(f"Fetching calendar from provider '{provider.name}'...")
        service = self._registry.get(provider)
        if service is None:
            logger.warning(f"No calendar service registered for provider '{provider.name}'")
            raise Exception(f"No calendar service registered for provider '{provider.name}'")
        result = service.get_calendar()

        if result.is_successful and result.value is not None:
            logger.debug(f"Successfully fetched calendar from provider '{provider.name}'")
            return RemoteCalendar(
                external_provider=provider,
                calendar_events=result.value.calendar_events,
            )
        else:
            logger.error(f"Failed to fetch calendar from provider '{provider.name}': {result.error_description}")
            raise Exception(f"Failed to fetch calendar from provider '{provider.name}': {result.error_description}")

    def _events_match(self, truth_event: CalendarEventInfo, remote_event: CalendarEventInfo) -> bool:
        return (
            truth_event.title == remote_event.title
            and truth_event.description == remote_event.description
            and truth_event.location == remote_event.location
            and truth_event.starts_at == remote_event.starts_at
            and truth_event.ends_at == remote_event.ends_at
        )

    def _resolve_event_status(
        self,
        truth_event: TruthCalendarEvent,
        remote_event: RemoteCalendarEvent,
    ) -> SyncStatus:
        
        if not self._events_match(truth_event.event_info, remote_event.event_info):
            return SyncStatus.BEHIND
        return SyncStatus.SYNCED

    def get_provider_calendar_sync_status(
    self,
    external_provider: ExternalProvider
) -> CalendarSyncResult:
        truth_calendar = self._get_truth_calendar()
        remote_calendar = self._get_provider_calendar(external_provider)
        
        provider_name = remote_calendar.external_provider.name
        logger.debug(f"Comparing calendars for provider '{provider_name}'...")

        truth_events = {e.id: e for e in truth_calendar.calendar_events}
        remote_events = {e.external_id: e for e in remote_calendar.calendar_events}
        logger.debug(f"Truth events: {len(truth_events)}, Remote events: {len(remote_events)}")

        mapped_external_ids: set[str] = set()
        event_results: list[EventSyncResult] = []

        for truth_id, truth_event in truth_events.items():
            mapping = self._mapping_store.get(truth_id, remote_calendar.external_provider)

            if mapping is None:
                logger.debug(f"[{provider_name}] Truth event {truth_id} has no mapping → BEHIND")
                event_results.append(EventSyncResult(
                    truth_event=truth_event,
                    remote_event=None,
                    sync_status=SyncStatus.BEHIND
                ))
            elif mapping.external_id not in remote_events:
                logger.warning(f"[{provider_name}] Truth event {truth_id} mapped to '{mapping.external_id}' but remote event is gone → BEHIND")
                event_results.append(EventSyncResult(
                    truth_event=truth_event,
                    remote_event=None,
                    sync_status=SyncStatus.BEHIND
                ))
            else:
                remote_event = remote_events[mapping.external_id]
                mapped_external_ids.add(mapping.external_id)
                status = self._resolve_event_status(truth_event, remote_event)
                logger.debug(f"[{provider_name}] Truth event {truth_id} ↔ remote '{mapping.external_id}' → {status.value}")
                event_results.append(EventSyncResult(
                    truth_event=truth_event,
                    remote_event=remote_event,
                    sync_status=status
                ))

        for external_id, remote_event in remote_events.items():
            if external_id not in mapped_external_ids:
                logger.debug(f"[{provider_name}] Remote event '{external_id}' has no truth counterpart → AHEAD")
                event_results.append(EventSyncResult(
                    truth_event=None,
                    remote_event=remote_event,
                    sync_status=SyncStatus.AHEAD
                ))

        logger.debug(f"[{provider_name}] Comparison complete: {len(event_results)} results")
        return CalendarSyncResult(remote_calendar=remote_calendar, event_statuses=event_results)

    def get_all_calendars_sync_status(self) -> SyncResult:
        calendar_sync_results: list[CalendarSyncResult] = []

        for provider, _ in self._registry.get_all():
            try:
                result = self.get_provider_calendar_sync_status(provider)
            except Exception as e:
                logger.warning(f"Skipping provider '{provider.name}': {e}")
                continue

            calendar_sync_results.append(result)

        return SyncResult(calendar_sync_statuses=calendar_sync_results)
    
    def sync_all(self) -> SyncResult:
        calendar_sync_results: list[CalendarSyncResult] = []

        for provider, service in self._registry.get_all():
            try:
                diff = self.get_provider_calendar_sync_status(provider)
            except Exception as e:
                logger.warning(f"Skipping provider '{provider.name}': {e}")
                continue

            for event_result in diff.event_statuses:
                self._apply_event_sync(provider, service, event_result)

            calendar_sync_results.append(diff)

        return SyncResult(calendar_sync_statuses=calendar_sync_results)

    def _apply_event_sync(
        self,
        provider: ExternalProvider,
        service: IRemoteCalendarService,
        event_result: EventSyncResult,
    ) -> None:
        if event_result.sync_status == SyncStatus.SYNCED:
            return

        if event_result.sync_status == SyncStatus.BEHIND:
            truth_event = event_result.truth_event
            assert truth_event is not None  # guaranteed by EventSyncResult's validator

            if event_result.remote_event is None:
                result = service.add_event(truth_event.event_info)
                if not result.is_successful or result.value is None:
                    logger.error(f"[{provider.name}] Failed to push event {truth_event.id}: {result.error_description}")
                    return
                external_id = result.value
            else:
                updated = RemoteCalendarEvent(
                    external_id=event_result.remote_event.external_id,
                    event_info=truth_event.event_info,
                )
                result = service.update_event(updated)
                if not result.is_successful or result.value is None:
                    logger.error(f"[{provider.name}] Failed to update event {truth_event.id}: {result.error_description}")
                    return
                external_id = result.value.external_id

            self._mapping_store.put(ExternalEventMapping(
                truth_event_id=truth_event.id,
                external_id=external_id,
                provider=provider,
                status=SyncStatus.SYNCED,
            ))
            logger.info(f"[{provider.name}] Synced truth event {truth_event.id} → remote '{external_id}'")

        elif event_result.sync_status == SyncStatus.AHEAD:
            remote_event = event_result.remote_event
            assert remote_event is not None

            result = service.remove_event(remote_event.external_id)
            if not result.is_successful:
                logger.error(f"[{provider.name}] Failed to remove orphan '{remote_event.external_id}': {result.error_description}")
                return
            logger.info(f"[{provider.name}] Removed orphaned remote event '{remote_event.external_id}'")