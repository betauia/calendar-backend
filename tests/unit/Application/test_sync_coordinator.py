# tests/unit/Application/test_sync_coordinator.py
import logging
import threading

import pytest
from unittest.mock import MagicMock, create_autospec

from Application.sync_coordinator import SyncCoordinator
from Application.sync_service import SyncService
from Application.models.result.sync_result import SyncResult

logger = logging.getLogger(__name__)

@pytest.fixture
def sync_service() -> MagicMock:
    return create_autospec(SyncService, instance=True)

@pytest.fixture
def coordinator(sync_service: SyncService) -> SyncCoordinator:
    return SyncCoordinator(sync_service=sync_service)


# --- Basic behavior ---

def test_request_sync_calls_sync_all_once_when_uncontended(
    coordinator: SyncCoordinator,
    sync_service: MagicMock,
) -> None:
    sync_service.sync_all.return_value = SyncResult(calendar_sync_statuses=[])

    coordinator.request_sync()

    sync_service.sync_all.assert_called_once()


def test_running_and_pending_flags_reset_after_completion(
    coordinator: SyncCoordinator,
    sync_service: MagicMock,
) -> None:
    sync_service.sync_all.return_value = SyncResult(calendar_sync_statuses=[])

    coordinator.request_sync()

    assert coordinator._running is False            # type: ignore
    assert coordinator._resync_pending is False     # type: ignore


# --- Coalescing under concurrency ---

def test_trigger_arriving_mid_run_coalesces_into_single_trailing_rerun(
    coordinator: SyncCoordinator,
    sync_service: MagicMock,
) -> None:
    first_call_started = threading.Event()
    release_first_call = threading.Event()
    call_count = 0
    call_lock = threading.Lock()

    def sync_all_side_effect() -> SyncResult:
        nonlocal call_count
        with call_lock:
            call_count += 1
            current_call = call_count
        if current_call == 1:
            first_call_started.set()
            release_first_call.wait(timeout=5)
        return SyncResult(calendar_sync_statuses=[])

    sync_service.sync_all.side_effect = sync_all_side_effect

    thread_a = threading.Thread(target=coordinator.request_sync)
    thread_a.start()
    assert first_call_started.wait(timeout=5), "first sync never started"

    for _ in range(5):
        coordinator.request_sync()

    assert coordinator._resync_pending is True      # type: ignore
    assert call_count == 1, "no second run should have started while first is in flight"

    release_first_call.set()
    thread_a.join(timeout=5)

    assert call_count == 2, "expected exactly one trailing re-run, not one per trigger"
    assert coordinator._running is False            # type: ignore
    assert coordinator._resync_pending is False     # type: ignore


def test_trigger_arriving_after_run_completes_starts_a_fresh_run(
    coordinator: SyncCoordinator,
    sync_service: MagicMock,
) -> None:
    sync_service.sync_all.return_value = SyncResult(calendar_sync_statuses=[])

    coordinator.request_sync()
    coordinator.request_sync()

    assert sync_service.sync_all.call_count == 2


# --- Failure handling ---

def test_exception_during_sync_releases_lock_and_propagates(
    coordinator: SyncCoordinator,
    sync_service: MagicMock,
) -> None:
    sync_service.sync_all.side_effect = ConnectionError("provider unreachable")

    with pytest.raises(ConnectionError):
        coordinator.request_sync()

    assert coordinator._running is False            # type: ignore


def test_new_sync_can_start_after_a_previous_run_failed(
    coordinator: SyncCoordinator,
    sync_service: MagicMock,
) -> None:
    sync_service.sync_all.side_effect = ConnectionError("provider unreachable")
    with pytest.raises(ConnectionError):
        coordinator.request_sync()

    sync_service.sync_all.side_effect = None
    sync_service.sync_all.return_value = SyncResult(calendar_sync_statuses=[])

    coordinator.request_sync()

    assert sync_service.sync_all.call_count == 2