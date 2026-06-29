# tests/Infrastructure/test_external_event_mapping_store.py
import logging
from datetime import datetime, timezone

import pytest
from pydantic import HttpUrl

from Domain.TruthCalendarEvent import CalendarEvent
from Domain.ExternalEventMapping import ExternalEventMapping
from Domain.ExternalProvider import ExternalProvider
from Domain.SyncStatus import SyncStatus
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore

logger = logging.getLogger(__name__)


@pytest.fixture
def store() -> ExternalEventMappingStore:
    return ExternalEventMappingStore()


@pytest.fixture
def provider() -> ExternalProvider:
    return ExternalProvider(name="Test Provider", url=HttpUrl("http://test-provider.com"))


@pytest.fixture
def other_provider() -> ExternalProvider:
    return ExternalProvider(name="Other Provider", url=HttpUrl("http://other-provider.com"))


@pytest.fixture
def sample_event() -> CalendarEvent:
    return CalendarEvent(
        id=1,
        title="Team meeting",
        description="Weekly sync",
        created_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        location="Discord",
        starts_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_mapping(sample_event: CalendarEvent, provider: ExternalProvider) -> ExternalEventMapping:
    return ExternalEventMapping(
        event=sample_event,
        provider=provider,
        external_id="ext-123",
        status=SyncStatus.SYNCED
    )


def test_put_creates_new_mapping(store: ExternalEventMappingStore, sample_mapping: ExternalEventMapping, provider: ExternalProvider):
    store.put(sample_mapping)
    result = store.get(1, provider)
    assert result is not None
    assert result.external_id == "ext-123"
    assert result.status == SyncStatus.SYNCED


def test_put_replaces_existing_mapping(store: ExternalEventMappingStore, sample_mapping: ExternalEventMapping, sample_event: CalendarEvent, provider: ExternalProvider):
    store.put(sample_mapping)

    updated_mapping = ExternalEventMapping(
        event=sample_event,
        provider=provider,
        external_id="ext-456",
        status=SyncStatus.BEHIND
    )
    store.put(updated_mapping)

    result = store.get(1, provider)
    assert result is not None
    assert result.external_id == "ext-456"
    assert result.status == SyncStatus.BEHIND


def test_get_returns_none_for_missing_mapping(store: ExternalEventMappingStore, provider: ExternalProvider):
    result = store.get(999, provider)
    assert result is None


def test_put_different_providers_stored_separately(store: ExternalEventMappingStore, sample_event: CalendarEvent, provider: ExternalProvider, other_provider: ExternalProvider):
    mapping_a = ExternalEventMapping(
        event=sample_event,
        provider=provider,
        external_id="ext-123",
        status=SyncStatus.SYNCED
    )
    mapping_b = ExternalEventMapping(
        event=sample_event,
        provider=other_provider,
        external_id="ext-456",
        status=SyncStatus.BEHIND
    )

    store.put(mapping_a)
    store.put(mapping_b)

    result_a = store.get(1, provider)
    result_b = store.get(1, other_provider)

    assert result_a is not None
    assert result_b is not None
    assert result_a.external_id == "ext-123"
    assert result_b.external_id == "ext-456"


def test_put_raises_if_event_id_is_none(store: ExternalEventMappingStore, provider: ExternalProvider):
    event_without_id = CalendarEvent(
        title="Team meeting",
        description="Weekly sync",
        created_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        location="Discord",
        starts_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
    )
    mapping = ExternalEventMapping(
        event=event_without_id,
        provider=provider,
        external_id="ext-123",
        status=SyncStatus.SYNCED
    )

    with pytest.raises(ValueError, match="Event id must not be None"):
        store.put(mapping)