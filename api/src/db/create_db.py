# create_db.py
from db.engine import ENGINE
from db.base import Base

import domain.generic_event
import domain.discord_event

Base.metadata.create_all(ENGINE)
