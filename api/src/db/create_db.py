# create_db.py
from db.engine import ENGINE
from api.src.db.db import Base

import api.src.domain.event
import domain.discord_event

Base.metadata.create_all(ENGINE)
