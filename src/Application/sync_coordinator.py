import logging
import threading

from Application.sync_service import SyncService

logger = logging.getLogger(__name__)

class SyncCoordinator:
    """Ensures sync runs never overlap, and coalesces triggers that
    arrive while a run is in progress into a single trailing re-run."""

    def __init__(self, sync_service: SyncService) -> None:
        self._sync_service = sync_service
        self._lock = threading.Lock()
        self._running = False
        self._resync_pending = False

    def request_sync(self) -> None:
        with self._lock:
            if self._running:
                self._resync_pending = True
                logger.debug("Sync already running, marking resync pending")
                return
            self._running = True

        self._run_loop()

    def _run_loop(self) -> None:
        try:
            while True:
                logger.info("Running sync across all providers...")
                self._sync_service.sync_all()  # or sync_all() once it pushes
                with self._lock:
                    if not self._resync_pending:
                        self._running = False
                        return
                    self._resync_pending = False
        except Exception:
            with self._lock:
                self._running = False
            raise