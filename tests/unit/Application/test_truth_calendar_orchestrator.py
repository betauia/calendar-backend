import logging
from datetime import datetime, timezone
from unittest.mock import create_autospec

import pytest

from Application.service_result import ErrorCode, ServiceResult
from Application.sync_coordinator import SyncCoordinator
from Application.truth_calendar_orchestrator import TruthCalendarOrchestrator
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.CalendarEventMetaInfo import CalendarEventMetaInfo
from Domain.TruthCalendar import TruthCalendar
from Domain.TruthCalendarEvent import TruthCalendarEvent
from Infrastructure.truth_calendar_service import TruthCalendarService

logger = logging.getLogger(__name__)

# --- Fixtures ---

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
def truth_calendar(truth_event: TruthCalendarEvent) -> TruthCalendar:
    return TruthCalendar(calendar_events=[truth_event])

@pytest.fixture
def truth_service() -> TruthCalendarService:
    return create_autospec(TruthCalendarService, instance=True)

@pytest.fixture
def sync_coordinator() -> SyncCoordinator:
    return create_autospec(SyncCoordinator, instance=True)

@pytest.fixture
def orchestrator(
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
) -> TruthCalendarOrchestrator:
    return TruthCalendarOrchestrator(
        truth_service=truth_service,
        sync_coordinator=sync_coordinator,
    )


# --- get_calendar / get_event_with_id: pure delegation, no sync trigger ---

def test_get_calendar_delegates_to_truth_service(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
    truth_calendar: TruthCalendar,
) -> None:
    truth_service.get_calendar.return_value = ServiceResult[TruthCalendar](  # type: ignore
        is_successful=True, value=truth_calendar
    )

    result = orchestrator.get_calendar()

    assert result.is_successful
    assert result.value == truth_calendar
    truth_service.get_calendar.assert_called_once()  # type: ignore
    sync_coordinator.request_sync.assert_not_called()  # type: ignore


def test_get_event_with_id_delegates_to_truth_service(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
    truth_event: TruthCalendarEvent,
) -> None:
    truth_service.get_event_with_id.return_value = ServiceResult[TruthCalendarEvent](  # type: ignore
        is_successful=True, value=truth_event
    )

    result = orchestrator.get_event_with_id(1)

    assert result.is_successful
    assert result.value == truth_event
    truth_service.get_event_with_id.assert_called_once_with(1)  # type: ignore
    sync_coordinator.request_sync.assert_not_called()  # type: ignore


# --- add_event ---

def test_add_event_success_triggers_sync(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
    event_info: CalendarEventInfo,
    truth_event: TruthCalendarEvent,
) -> None:
    truth_service.add_event.return_value = ServiceResult[TruthCalendarEvent](  # type: ignore
        is_successful=True, value=truth_event
    )

    result = orchestrator.add_event(event_info)

    assert result.is_successful
    truth_service.add_event.assert_called_once_with(event_info)  # type: ignore
    sync_coordinator.request_sync.assert_called_once()  # type: ignore


def test_add_event_failure_does_not_trigger_sync(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
    event_info: CalendarEventInfo,
) -> None:
    truth_service.add_event.return_value = ServiceResult[TruthCalendarEvent](  # type: ignore
        is_successful=False, error_code=ErrorCode.UNKNOWN, error_description="db error"
    )

    result = orchestrator.add_event(event_info)

    assert not result.is_successful
    sync_coordinator.request_sync.assert_not_called()  # type: ignore


# --- update_event ---

def test_update_event_success_triggers_sync(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
    event_info: CalendarEventInfo,
    truth_event: TruthCalendarEvent,
) -> None:
    truth_service.update_event.return_value = ServiceResult[TruthCalendarEvent](  # type: ignore
        is_successful=True, value=truth_event
    )

    result = orchestrator.update_event(1, event_info)

    assert result.is_successful
    truth_service.update_event.assert_called_once_with(1, event_info)  # type: ignore
    sync_coordinator.request_sync.assert_called_once()  # type: ignore


def test_update_event_failure_does_not_trigger_sync(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
    event_info: CalendarEventInfo,
) -> None:
    truth_service.update_event.return_value = ServiceResult[TruthCalendarEvent](  # type: ignore
        is_successful=False, error_code=ErrorCode.NOT_FOUND, error_description="not found"
    )

    result = orchestrator.update_event(999, event_info)

    assert not result.is_successful
    sync_coordinator.request_sync.assert_not_called()  # type: ignore


# --- remove_event ---

def test_remove_event_success_triggers_sync(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
) -> None:
    truth_service.remove_event.return_value = ServiceResult[None](is_successful=True)  # type: ignore

    result = orchestrator.remove_event(1)

    assert result.is_successful
    truth_service.remove_event.assert_called_once_with(1)  # type: ignore
    sync_coordinator.request_sync.assert_called_once()  # type: ignore


def test_remove_event_failure_does_not_trigger_sync(
    orchestrator: TruthCalendarOrchestrator,
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
) -> None:
    truth_service.remove_event.return_value = ServiceResult[None](  # type: ignore
        is_successful=False, error_code=ErrorCode.NOT_FOUND, error_description="not found"
    )

    result = orchestrator.remove_event(999)

    assert not result.is_successful
    sync_coordinator.request_sync.assert_not_called()  # type: ignore