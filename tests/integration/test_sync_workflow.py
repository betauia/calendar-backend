import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from unittest.mock import create_autospec

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


# --- Providers: two "stumped" (wrongly configured / unreachable) plugins,
# one that actually works — matching the shape of a real providers.yaml. ---

@pytest.fixture
def discord_provider() -> ExternalProvider:
    return ExternalProvider(name="Discord", url=HttpUrl("https://discord.com"))


@pytest.fixture
def google_provider() -> ExternalProvider:
    return ExternalProvider(name="Google", url=HttpUrl("https://google.com"))


@pytest.fixture
def working_provider() -> ExternalProvider:
    return ExternalProvider(
        name="ActualPluginThatShouldWork", url=HttpUrl("http://localhost:8000/api")
    )


@pytest.fixture
def providers_config(
    discord_provider: ExternalProvider,
    google_provider: ExternalProvider,
    working_provider: ExternalProvider,
) -> ProvidersConfig:
    # Order matters — the endpoint should preserve configured order in its response.
    return ProvidersConfig(
        external_providers=[discord_provider, google_provider, working_provider]
    )


def _make_unreachable_service(provider: ExternalProvider) -> IRemoteCalendarService:
    """Mimics what the real RemoteCalendarService reports for an
    httpx.ConnectError — a wrongly configured or dead plugin."""
    service = create_autospec(IRemoteCalendarService, instance=True)
    failure = ServiceResult[RemoteCalendar](
        is_successful=False,
        error_code=ErrorCode.CONNECTION_ERROR,
        error_description=f"Could not connect to {provider.url}",
    )
    service.get_calendar.return_value = failure  # type: ignore
    return service


def _make_working_service(provider: ExternalProvider) -> IRemoteCalendarService:
    """Stateful fake: reflects pushed events on subsequent get_calendar()
    calls, the same way a real, reachable plugin would."""
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

    service.get_calendar.side_effect = get_calendar_side_effect  # type: ignore
    service.add_event.side_effect = add_event_side_effect  # type: ignore
    return service


@pytest.fixture
def discord_service(discord_provider: ExternalProvider) -> IRemoteCalendarService:
    return _make_unreachable_service(discord_provider)


@pytest.fixture
def google_service(google_provider: ExternalProvider) -> IRemoteCalendarService:
    return _make_unreachable_service(google_provider)


@pytest.fixture
def working_service(working_provider: ExternalProvider) -> IRemoteCalendarService:
    return _make_working_service(working_provider)


@pytest.fixture
def registry(
    discord_provider: ExternalProvider,
    discord_service: IRemoteCalendarService,
    google_provider: ExternalProvider,
    google_service: IRemoteCalendarService,
    working_provider: ExternalProvider,
    working_service: IRemoteCalendarService,
) -> CalendarServiceRegistry:
    registry = CalendarServiceRegistry()
    registry.register(discord_provider, discord_service)
    registry.register(google_provider, google_service)
    registry.register(working_provider, working_service)
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


# --- Tests ---

def test_add_event_succeeds_despite_two_broken_providers(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    """Truth-calendar writes shouldn't be held hostage by any dead plugin,
    even when the majority of configured providers are unreachable."""
    response = client.post("/events", json=event_payload)
    assert response.status_code == 200


def test_get_all_sync_status_returns_200_with_mixed_results(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    client.post("/events", json=event_payload)

    response = client.get("/sync-status")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_all_sync_status_reports_broken_providers_as_errors_in_configured_order(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    client.post("/events", json=event_payload)

    data = client.get("/sync-status").json()
    by_provider = {entry["provider"]: entry for entry in data}

    assert by_provider["Discord"] == {
        "provider": "Discord",
        "error_code": "connection_error",
        "error_description": "Failed to fetch calendar from provider 'Discord': Could not connect to https://discord.com/",
    }
    assert by_provider["Google"] == {
        "provider": "Google",
        "error_code": "connection_error",
        "error_description": "Failed to fetch calendar from provider 'Google': Could not connect to https://google.com/",
    }


def test_get_all_sync_status_reports_working_provider_with_counts(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    client.post("/events", json=event_payload)
    client.post("/events", json=event_payload)  # second event → 2 synced total

    data = client.get("/sync-status").json()
    working_entry = next(
        entry
        for entry in data
        if entry["provider"] == "ActualPluginThatShouldWork"
    )

    assert working_entry["provider"] == "ActualPluginThatShouldWork"
    assert working_entry["counts"] == {"ahead": 0, "behind": 0, "synced": 2}
    assert "error_code" not in working_entry


def test_get_sync_status_for_specific_broken_provider_still_returns_502(
    client: TestClient,
) -> None:
    """The single-provider endpoint keeps its original semantics — asking
    about one specific provider still surfaces the failure as an HTTP error,
    unlike the aggregate endpoint above."""
    response = client.get("/sync-status/discord")

    assert response.status_code == 502
    assert response.json()["detail"]["error_code"] == "connection_error"


def test_get_sync_status_for_working_provider_returns_counts(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    client.post("/events", json=event_payload)

    response = client.get("/sync-status/ActualPluginThatShouldWork")

    assert response.status_code == 200
    assert response.json()["counts"]["synced"] == 1