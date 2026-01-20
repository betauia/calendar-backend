from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from db.engine import ENGINE
from domain.generic_event import GenericEvent


def seed():
    with Session(ENGINE) as session:
        # Idempotency: do nothing if already seeded
        existing = session.query(GenericEvent).count()
        if existing > 0:
            print(f"DB already seeded ({existing} events). Skipping.")
            return

        now = datetime.now(tz=timezone.utc)

        events = [
            GenericEvent(
                provider="generic",
                name="Movie Night",
                description="Watch party",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=2),
            ),
            GenericEvent(
                provider="generic",
                name="Planning Meeting",
                description="Sprint planning",
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=2, hours=1),
            ),
            GenericEvent(
                provider="generic",
                name="Game Night",
                description="Board games",
                start_time=now + timedelta(days=3),
                end_time=now + timedelta(days=3, hours=3),
            ),
        ]

        session.add_all(events)
        session.commit()

        print(f"Seeded {len(events)} GenericEvents")


if __name__ == "__main__":
    seed()
