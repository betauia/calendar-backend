# tests/test_truth_calendar_service.py
import logging
from unittest.mock import MagicMock, patch

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

from Infrastructure.truth_calendar_service import TruthCalendarService
from Application.service_result import ErrorCode
from Domain.TruthCalendarEvent import CalendarEvent

logger = logging.getLogger(__name__)

@pytest.fixture
def service():
    return TruthCalendarService(connection_string="sqlite:///test_truth_calendar.db")

@pytest.fixture
def sample_event():
    return CalendarEvent(
        title="Team meeting",
        description="Weekly sync",
        created_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        location="Discord",
        starts_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
    )

@pytest.fixture
def failing_session_factory():
    mock_factory = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    mock_factory.return_value = mock_session
    return mock_factory, mock_session

def test_get_calendar_empty(service: TruthCalendarService):
    result = service.get_calendar()
    assert result.is_successful
    assert result.value is not None
    assert result.value.calendar_events == []

def test_add_event(service: TruthCalendarService, sample_event: CalendarEvent):
    result = service.add_event(sample_event)
    assert result.is_successful
    assert result.value is not None
    assert result.value.title == "Team meeting"
    assert result.value.id is not None

    calendar_result = service.get_calendar()
    assert calendar_result.is_successful
    assert calendar_result.value is not None
    assert len(calendar_result.value.calendar_events) == 1

def test_add_event_database_error(service: TruthCalendarService, sample_event: CalendarEvent, failing_session_factory: tuple[MagicMock, MagicMock]):
    mock_factory, mock_session = failing_session_factory
    with patch.object(service, "_session_factory", mock_factory):
        result = service.add_event(sample_event)
        assert not result.is_successful
        assert result.error_code == ErrorCode.UNKNOWN
        mock_session.rollback.assert_called_once()

def test_update_event(service: TruthCalendarService, sample_event: CalendarEvent):
    add_result = service.add_event(sample_event)
    assert add_result.value is not None

    updated = add_result.value.model_copy(update={"title": "Updated meeting"})
    update_result = service.update_event(updated)
    assert update_result.is_successful
    assert update_result.value is not None
    assert update_result.value.title == "Updated meeting"

def test_update_nonexistent_event(service: TruthCalendarService, sample_event: CalendarEvent):
    sample_event_with_id = sample_event.model_copy(update={"id": 999})
    result = service.update_event(sample_event_with_id)
    assert not result.is_successful
    assert result.error_code == ErrorCode.NOT_FOUND

def test_update_event_database_error(service: TruthCalendarService, sample_event: CalendarEvent, failing_session_factory: tuple[MagicMock, MagicMock]):
    add_result = service.add_event(sample_event)
    assert add_result.value is not None

    updated = add_result.value.model_copy(update={"title": "Updated meeting"})
    mock_factory, mock_session = failing_session_factory
    with patch.object(service, "_session_factory", mock_factory):
        result = service.update_event(updated)
        assert not result.is_successful
        assert result.error_code == ErrorCode.UNKNOWN
        mock_session.rollback.assert_called_once()

def test_remove_event(service: TruthCalendarService, sample_event: CalendarEvent):
    add_result = service.add_event(sample_event)
    assert add_result.value is not None
    assert add_result.value.id is not None

    remove_result = service.remove_event(add_result.value.id)
    assert remove_result.is_successful

    calendar_result = service.get_calendar()
    assert calendar_result.value is not None
    assert calendar_result.value.calendar_events == []

def test_remove_nonexistent_event(service: TruthCalendarService):
    result = service.remove_event(999)
    assert not result.is_successful
    assert result.error_code == ErrorCode.NOT_FOUND

def test_remove_event_database_error(service: TruthCalendarService, sample_event: CalendarEvent, failing_session_factory: tuple[MagicMock, MagicMock]):
    add_result = service.add_event(sample_event)
    assert add_result.value is not None
    assert add_result.value.id is not None

    mock_factory, mock_session = failing_session_factory
    mock_session.get.return_value = MagicMock()
    with patch.object(service, "_session_factory", mock_factory):
        result = service.remove_event(add_result.value.id)
        assert not result.is_successful
        assert result.error_code == ErrorCode.UNKNOWN
        mock_session.rollback.assert_called_once()