import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from unittest.mock import create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from Application.calendar_service_registry import CalendarServiceRegistry
from Application.i_remote_calendar_service import IRemoteCalendarService
from Application.service_result import ErrorCode, ServiceResult
from Application.sync_coordinator import SyncCoordinator
from Application.sync_service import SyncService
from Application.truth_calendar_orchestrator import TruthCalendarOrchestrator
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.ExternalProvider import ExternalProvider
from Domain.ProvidersConfig import ProvidersConfig
from Domain.RemoteCalendar import RemoteCalendar
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore
from Infrastructure.truth_calendar_service import TruthCalendarService
from Presentation.routes import Routes

logger = logging.getLogger(__name__)


# --- Fixtures: real infra, wired the same way main.py does it.
# The remote provider mock is stateful and now supports update_event too,
# so a PUT can actually be observed reflecting back into the remote calendar
# the same way a real, reachable plugin would. ---

@pytest.fixture
def provider() -> ExternalProvider:
    return ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))


@pytest.fixture
def providers_config(provider: ExternalProvider) -> ProvidersConfig:
    return ProvidersConfig(external_providers=[provider])


@pytest.fixture
def mock_remote_service(provider: ExternalProvider) -> IRemoteCalendarService:
    service = create_autospec(IRemoteCalendarService, instance=True)
    remote_events: list[RemoteCalendarEvent] = []

    def get_calendar_side_effect() -> ServiceResult[RemoteCalendar]:
        return ServiceResult[RemoteCalendar](
            is_successful=True,
            value=RemoteCalendar(
                external_provider=provider, calendar_events=list(remote_events)
            ),
        )

    def add_event_side_effect(event_info: CalendarEventInfo) -> ServiceResult[str]:
        external_id = f"remote-ext-{len(remote_events) + 1}"
        remote_events.append(
            RemoteCalendarEvent(external_id=external_id, event_info=event_info)
        )
        return ServiceResult[str](is_successful=True, value=external_id)

    def update_event_side_effect(
        updated_event: RemoteCalendarEvent,
    ) -> ServiceResult[RemoteCalendarEvent]:
        for i, existing in enumerate(remote_events):
            if existing.external_id == updated_event.external_id:
                remote_events[i] = updated_event
                return ServiceResult[RemoteCalendarEvent](
                    is_successful=True, value=updated_event
                )
        return ServiceResult[RemoteCalendarEvent](
            is_successful=False,
            error_code=ErrorCode.NOT_FOUND,
            error_description=f"Event {updated_event.external_id} not found",
        )

    service.get_calendar.side_effect = get_calendar_side_effect  # type: ignore
    service.add_event.side_effect = add_event_side_effect  # type: ignore
    service.update_event.side_effect = update_event_side_effect  # type: ignore
    return service


@pytest.fixture
def registry(
    provider: ExternalProvider, mock_remote_service: IRemoteCalendarService
) -> CalendarServiceRegistry:
    registry = CalendarServiceRegistry()
    registry.register(provider, mock_remote_service)
    return registry


@pytest.fixture
def truth_service(tmp_path: Path) -> TruthCalendarService:
    db_path = tmp_path / "truth_calendar.db"
    return TruthCalendarService(connection_string=f"sqlite:///{db_path}")


@pytest.fixture
def mapping_store() -> ExternalEventMappingStore:
    return ExternalEventMappingStore()


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


@pytest.fixture
def sync_coordinator(sync_service: SyncService) -> SyncCoordinator:
    return SyncCoordinator(sync_service=sync_service)


@pytest.fixture
def orchestrator(
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
) -> TruthCalendarOrchestrator:
    return TruthCalendarOrchestrator(
        truth_service=truth_service,
        sync_coordinator=sync_coordinator,
    )


@pytest.fixture
def client(
    sync_service: SyncService,
    sync_coordinator: SyncCoordinator,
    orchestrator: TruthCalendarOrchestrator,
    providers_config: ProvidersConfig,
) -> TestClient:
    routes = Routes(
        sync_service=sync_service,
        sync_coordinator=sync_coordinator,
        truth_calendar_orchestrator=orchestrator,
        providers=providers_config,
    )
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def event_payload() -> dict[str, str]:
    return {
        "title": "Standup",
        "description": "Daily sync",
        "location": "Online",
        "starts_at": datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc).isoformat(),
        "ends_at": datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc).isoformat(),
    }


@pytest.fixture
def updated_event_payload(event_payload: dict[str, str]) -> dict[str, str]:
    return {
        **event_payload,
        "title": "Standup (rescheduled)",
        "location": "Conference Room B",
    }


# --- Tests: every assertion below is made against API responses only,
# except the one explicit peek at the mock provider (see comment below). ---

def test_update_event_persists_change(
    client: TestClient,
    event_payload: dict[str, str],
    updated_event_payload: dict[str, str],
) -> None:
    create_response = client.post("/events", json=event_payload)
    event_id = create_response.json()["id"]

    update_response = client.put(f"/events/{event_id}", json=updated_event_payload)

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["id"] == event_id
    assert body["event_info"]["title"] == "Standup (rescheduled)"
    assert body["event_info"]["location"] == "Conference Room B"

    get_response = client.get(f"/events/{event_id}")
    assert get_response.json()["event_info"]["title"] == "Standup (rescheduled)"


def test_update_event_triggers_sync_and_propagates_to_provider(
    client: TestClient,
    event_payload: dict[str, str],
    updated_event_payload: dict[str, str],
    mock_remote_service: IRemoteCalendarService,
) -> None:
    create_response = client.post("/events", json=event_payload)
    event_id = create_response.json()["id"]
    mock_remote_service.add_event.assert_called_once()  # type: ignore

    update_response = client.put(f"/events/{event_id}", json=updated_event_payload)
    assert update_response.status_code == 200

    # SyncCoordinator.request_sync() runs synchronously in-thread, so by the
    # time the response comes back the (mocked) provider has already been hit.
    # This is the one place we peek behind the API, since the mock IS the
    # "provider" and there's no other observable proof of the outbound push.
    mock_remote_service.update_event.assert_called_once()  # type: ignore
    called_update = cast(
        RemoteCalendarEvent,
        mock_remote_service.update_event.call_args[0][0],  # type: ignore
    )
    assert called_update.external_id == "remote-ext-1"
    assert called_update.event_info.title == "Standup (rescheduled)"


def test_update_event_is_reflected_as_synced_via_sync_status_endpoint(
    client: TestClient,
    event_payload: dict[str, str],
    updated_event_payload: dict[str, str],
) -> None:
    create_response = client.post("/events", json=event_payload)
    event_id = create_response.json()["id"]

    client.put(f"/events/{event_id}", json=updated_event_payload)

    status_response = client.get("/sync-status/discord")

    assert status_response.status_code == 200
    assert status_response.json()["counts"] == {"ahead": 0, "behind": 0, "synced": 1}


def test_update_nonexistent_event_returns_404(
    client: TestClient, updated_event_payload: dict[str, str]
) -> None:
    response = client.put("/events/999", json=updated_event_payload)

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"