import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pydantic import HttpUrl
import pytest
import httpx

from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.RemoteCalendar import RemoteCalendar
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Infrastructure.remote_calendar_service import RemoteCalendarService
from Application.service_result import ErrorCode
from Domain.ExternalProvider import ExternalProvider

logger = logging.getLogger(__name__)


@pytest.fixture
def provider():
    return ExternalProvider(name="Test Provider", url=HttpUrl("http://test-provider.com"))


@pytest.fixture
def service(provider: ExternalProvider):
    return RemoteCalendarService(provider=provider)


@pytest.fixture
def sample_dto():
    return CalendarEventInfo(
        title="Team meeting",
        description="Weekly sync",
        location="Discord",
        starts_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_remote_event(sample_dto: CalendarEventInfo):
    return RemoteCalendarEvent(external_id="remote-abc123", event_info=sample_dto)


@pytest.fixture
def sample_remote_calendar(provider: ExternalProvider, sample_remote_event: RemoteCalendarEvent):
    return RemoteCalendar(external_provider=provider, calendar_events=[sample_remote_event])


# ── context manager ───────────────────────────────────────────

def test_context_manager(provider: ExternalProvider):
    with RemoteCalendarService(provider=provider) as service:
        assert service is not None


def test_context_manager_closes_client(provider: ExternalProvider):
    with RemoteCalendarService(provider=provider) as service:
        pass

    with pytest.raises(RuntimeError, match="client has been closed"):
        service.get_calendar()


# ── get_calendar ──────────────────────────────────────────────

def test_get_calendar_success(service: RemoteCalendarService, sample_remote_calendar: RemoteCalendar):
    mock_response = MagicMock()
    mock_response.json.return_value = sample_remote_calendar.model_dump(mode="json")
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.get.return_value = mock_response
        result = service.get_calendar()

    assert result.is_successful
    assert result.value is not None
    assert len(result.value.calendar_events) == 1
    assert result.value.calendar_events[0].external_id == "remote-abc123"
    assert result.value.calendar_events[0].event_info.title == "Team meeting"


def test_get_calendar_connection_error(service: RemoteCalendarService):
    with patch.object(service, "_client") as mock_client:
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        result = service.get_calendar()

    assert not result.is_successful
    assert result.error_code == ErrorCode.CONNECTION_ERROR


def test_get_calendar_http_error(service: RemoteCalendarService):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500)
    )

    with patch.object(service, "_client") as mock_client:
        mock_client.get.return_value = mock_response
        result = service.get_calendar()

    assert not result.is_successful
    assert result.error_code == ErrorCode.UNKNOWN


# ── add_event ─────────────────────────────────────────────────

def test_add_event_success(service: RemoteCalendarService, sample_dto: CalendarEventInfo):
    mock_response = MagicMock()
    mock_response.json.return_value = "remote-abc123"
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.post.return_value = mock_response
        result = service.add_event(sample_dto)

    assert result.is_successful
    assert result.value == "remote-abc123"


def test_add_event_connection_error(service: RemoteCalendarService, sample_dto: CalendarEventInfo):
    with patch.object(service, "_client") as mock_client:
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        result = service.add_event(sample_dto)

    assert not result.is_successful
    assert result.error_code == ErrorCode.CONNECTION_ERROR


def test_add_event_http_error(service: RemoteCalendarService, sample_dto: CalendarEventInfo):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500)
    )

    with patch.object(service, "_client") as mock_client:
        mock_client.post.return_value = mock_response
        result = service.add_event(sample_dto)

    assert not result.is_successful
    assert result.error_code == ErrorCode.UNKNOWN


# ── update_event ──────────────────────────────────────────────

def test_update_event_success(service: RemoteCalendarService, sample_remote_event: RemoteCalendarEvent):
    updated_event_info = sample_remote_event.event_info.model_copy(update={"title": "Updated meeting"})
    updated_remote_event = RemoteCalendarEvent(external_id=sample_remote_event.external_id, event_info=updated_event_info)

    mock_response = MagicMock()
    mock_response.json.return_value = updated_remote_event.model_dump(mode="json")
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.put.return_value = mock_response
        result = service.update_event(updated_remote_event)

    assert result.is_successful
    assert result.value is not None
    assert result.value.event_info.title == "Updated meeting"
    assert result.value.external_id == sample_remote_event.external_id


def test_update_event_not_found(service: RemoteCalendarService, sample_remote_event: RemoteCalendarEvent):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404)
    )

    with patch.object(service, "_client") as mock_client:
        mock_client.put.return_value = mock_response
        result = service.update_event(sample_remote_event)

    assert not result.is_successful
    assert result.error_code == ErrorCode.NOT_FOUND


def test_update_event_connection_error(service: RemoteCalendarService, sample_remote_event: RemoteCalendarEvent):
    with patch.object(service, "_client") as mock_client:
        mock_client.put.side_effect = httpx.ConnectError("Connection refused")
        result = service.update_event(sample_remote_event)

    assert not result.is_successful
    assert result.error_code == ErrorCode.CONNECTION_ERROR


def test_update_event_http_error(service: RemoteCalendarService, sample_remote_event: RemoteCalendarEvent):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500)
    )

    with patch.object(service, "_client") as mock_client:
        mock_client.put.return_value = mock_response
        result = service.update_event(sample_remote_event)

    assert not result.is_successful
    assert result.error_code == ErrorCode.UNKNOWN


# ── remove_event ──────────────────────────────────────────────

def test_remove_event_success(service: RemoteCalendarService):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.delete.return_value = mock_response
        result = service.remove_event("remote-abc123")

    assert result.is_successful
    assert result.value is None


def test_remove_event_not_found(service: RemoteCalendarService):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404)
    )

    with patch.object(service, "_client") as mock_client:
        mock_client.delete.return_value = mock_response
        result = service.remove_event("remote-abc123")

    assert not result.is_successful
    assert result.error_code == ErrorCode.NOT_FOUND


def test_remove_event_connection_error(service: RemoteCalendarService):
    with patch.object(service, "_client") as mock_client:
        mock_client.delete.side_effect = httpx.ConnectError("Connection refused")
        result = service.remove_event("remote-abc123")

    assert not result.is_successful
    assert result.error_code == ErrorCode.CONNECTION_ERROR


def test_remove_event_http_error(service: RemoteCalendarService):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500)
    )

    with patch.object(service, "_client") as mock_client:
        mock_client.delete.return_value = mock_response
        result = service.remove_event("remote-abc123")

    assert not result.is_successful
    assert result.error_code == ErrorCode.UNKNOWN