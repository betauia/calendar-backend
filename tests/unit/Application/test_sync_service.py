import logging

import pytest
from datetime import datetime, timezone
from pydantic import HttpUrl
from unittest.mock import create_autospec

from Application.sync_service import SyncService
from Application.calendar_service_registry import CalendarServiceRegistry
from Application.i_remote_calendar_service import IRemoteCalendarService
from Application.models.result.calendar_sync_result import CalendarSyncResult
from Application.service_result import ServiceResult
from Domain.CalendarEventMetaInfo import CalendarEventMetaInfo
from Domain.SyncStatus import SyncStatus
from Domain.ExternalProvider import ExternalProvider
from Domain.ExternalEventMapping import ExternalEventMapping
from Domain.TruthCalendar import TruthCalendar
from Domain.TruthCalendarEvent import TruthCalendarEvent
from Domain.RemoteCalendar import RemoteCalendar
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Domain.CalendarEventInfo import CalendarEventInfo
from Infrastructure.truth_calendar_service import TruthCalendarService
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore


logger = logging.getLogger(__name__)

# --- Fixtures ---

@pytest.fixture
def provider() -> ExternalProvider:
    return ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))

@pytest.fixture
def event_info() -> CalendarEventInfo:
    return CalendarEventInfo(
        title="Standup",
        description="Daily standup",
        location="Online",
        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
    )

@pytest.fixture
def event_meta_info() -> CalendarEventMetaInfo:
    return CalendarEventMetaInfo(
        created_at=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
    )

@pytest.fixture
def truth_event(event_info: CalendarEventInfo, event_meta_info: CalendarEventMetaInfo) -> TruthCalendarEvent:
    return TruthCalendarEvent(id=1, event_info=event_info, event_meta_info=event_meta_info)

@pytest.fixture
def remote_event(event_info: CalendarEventInfo) -> RemoteCalendarEvent:
    return RemoteCalendarEvent(external_id="ext-001", event_info=event_info)

@pytest.fixture
def truth_calendar(truth_event: TruthCalendarEvent) -> TruthCalendar:
    return TruthCalendar(calendar_events=[truth_event])

@pytest.fixture
def remote_calendar(provider: ExternalProvider, remote_event: RemoteCalendarEvent) -> RemoteCalendar:
    return RemoteCalendar(external_provider=provider, calendar_events=[remote_event])

@pytest.fixture
def mapping_store() -> ExternalEventMappingStore:
    return create_autospec(ExternalEventMappingStore, instance=True, spec_set=True)  # type: ignore

@pytest.fixture
def truth_service(truth_calendar: TruthCalendar) -> TruthCalendarService:
    service = create_autospec(TruthCalendarService, instance=True)
    service.get_calendar.return_value = ServiceResult[TruthCalendar](  # type: ignore
        is_successful=True, value=truth_calendar
    )
    return service

@pytest.fixture
def remote_service(remote_calendar: RemoteCalendar) -> IRemoteCalendarService:
    service = create_autospec(IRemoteCalendarService, instance=True)
    service.get_calendar.return_value = ServiceResult[RemoteCalendar](  # type: ignore
        is_successful=True, value=remote_calendar
    )
    return service

@pytest.fixture
def registry(remote_service: IRemoteCalendarService) -> CalendarServiceRegistry:
    registry = create_autospec(CalendarServiceRegistry, instance=True)
    registry.get.return_value = remote_service  # type: ignore
    return registry

@pytest.fixture
def sync_service(
    truth_service: TruthCalendarService,
    registry: CalendarServiceRegistry,
    mapping_store: ExternalEventMappingStore,
) -> SyncService:
    return SyncService(
        truth_service=truth_service,
        registry=registry,
        mapping_store=mapping_store,
    )


# --- Tests ---

def test_truth_event_with_no_mapping_is_behind(
    sync_service: SyncService,
    mapping_store: ExternalEventMappingStore,
    provider: ExternalProvider,
) -> None:
    mapping_store.get.return_value = None  # type: ignore

    result: CalendarSyncResult = sync_service.get_provider_calendar_sync_status(provider)

    assert len(result.event_statuses) == 2
    behind = [e for e in result.event_statuses if e.sync_status == SyncStatus.BEHIND]
    ahead = [e for e in result.event_statuses if e.sync_status == SyncStatus.AHEAD]
    assert len(behind) == 1 and behind[0].truth_event is not None
    assert len(ahead) == 1 and ahead[0].remote_event is not None


def test_truth_event_with_matching_remote_is_synced(
    sync_service: SyncService,
    mapping_store: ExternalEventMappingStore,
    provider: ExternalProvider,
) -> None:
    mapping_store.get.return_value = ExternalEventMapping(  # type: ignore
        truth_event_id=1,
        external_id="ext-001",
        provider=provider,
        status=SyncStatus.SYNCED,
    )

    result: CalendarSyncResult = sync_service.get_provider_calendar_sync_status(provider)

    assert len(result.event_statuses) == 1
    assert result.event_statuses[0].sync_status == SyncStatus.SYNCED


def test_remote_event_with_no_truth_counterpart_is_ahead(
    sync_service: SyncService,
    mapping_store: ExternalEventMappingStore,
    truth_calendar: TruthCalendar,
    provider: ExternalProvider,
) -> None:
    mapping_store.get.return_value = None  # type: ignore
    truth_calendar.calendar_events.clear()  # no truth events

    result: CalendarSyncResult = sync_service.get_provider_calendar_sync_status(provider)

    assert len(result.event_statuses) == 1
    assert result.event_statuses[0].sync_status == SyncStatus.AHEAD
    assert result.event_statuses[0].truth_event is None