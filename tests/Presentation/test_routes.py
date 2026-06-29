from datetime import datetime, timezone
from unittest.mock import create_autospec

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from src.Application.models.result.calendar_sync_result import CalendarSyncResult
from src.Application.models.result.event_sync_result import EventSyncResult
from src.Application.sync_service import SyncService
from src.Domain.CalendarEventInfo import CalendarEventInfo
from src.Domain.ExternalProvider import ExternalProvider
from src.Domain.RemoteCalendar import RemoteCalendar
from src.Domain.RemoteCalendarEvent import RemoteCalendarEvent
from src.Domain.SyncStatus import SyncStatus
from src.Presentation.routes import router


def test_sync_status_endpoint_returns_provider_summary() -> None:
    app = FastAPI()
    app.include_router(router)

    provider = ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))
    app.state.providers = [provider]

    sync_service = create_autospec(SyncService, instance=True)
    sync_service.get_provider_calendar_sync_status.return_value = CalendarSyncResult(
        remote_calendar=RemoteCalendar(
            external_provider=provider,
            calendar_events=[
                RemoteCalendarEvent(
                    external_id="ext-1",
                    event_info=CalendarEventInfo(
                        title="Standup",
                        description="Daily",
                        location="Online",
                        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
                        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
                    ),
                )
            ],
        ),
        event_statuses=[
            EventSyncResult(
                truth_event=None,
                remote_event=RemoteCalendarEvent(
                    external_id="ext-1",
                    event_info=CalendarEventInfo(
                        title="Standup",
                        description="Daily",
                        location="Online",
                        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
                        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
                    ),
                ),
                sync_status=SyncStatus.AHEAD,
            )
        ],
    )
    app.state.sync_service = sync_service

    client = TestClient(app)
    response = client.get("/syncStatus")

    assert response.status_code == 200
    assert response.json()["provider"] == "Discord"
    assert response.json()["counts"]["ahead"] == 1
