# domain/discord_event.py
from sqlalchemy import (
    Column,
    ForeignKey,
    BigInteger,
    String,
    Integer,
)
from domain.generic_event import GenericEvent

class DiscordEvent(GenericEvent):
    __tablename__ = "DiscordEvents"

    # PK = FK enforces 1:1
    id = Column(
        String,
        ForeignKey("Events.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Discord-specific identity
    discord_event_id = Column(BigInteger, unique=True)
    guild_id = Column(BigInteger, nullable=False)

    # create_scheduled_event params
    entity_type = Column(Integer, nullable=False)
    privacy_level = Column(Integer, nullable=False)

    channel_id = Column(BigInteger)
    location = Column(String)
    image = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": "discord",
    }
