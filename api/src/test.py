# app.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List
from datetime import datetime
from pathlib import Path
import uvicorn
import yaml
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey
import asyncio

# ---------- CONFIG ----------
class Provider(BaseModel):
    name: str
    url: HttpUrl

class Config(BaseModel):
    external_providers: List[Provider]

    @classmethod
    def load(cls, path: str = "providers.yaml"):
        # Go up from src/ to project root
        config_path = Path(__file__).parent.parent /"config" / path
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

config = Config.load()

# ---------- DATABASE ----------
DATABASE_URL = "sqlite+aiosqlite:///./events.db"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase): pass

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)

class SyncState(Base):
    __tablename__ = "sync_state"
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String, primary_key=True)
    external_event_id: Mapped[str] = mapped_column(String)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---------- CORE LOGIC ----------
async def save_event(session: AsyncSession, dto: EventCreateDTO) -> Event:
    event = Event(title=dto.title, start_time=dto.start_time, end_time=dto.end_time)
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event

async def record_sync(session: AsyncSession, event_id: int, provider_name: str, external_event_id: str):
    state = SyncState(event_id=event_id, provider_name=provider_name, external_event_id=external_event_id)
    session.add(state)
    await session.commit()

async def push_to_provider(event: Event, provider: Provider):
    async with httpx.AsyncClient() as client:
        resp = await client.post(str(provider.url), json={
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
        })
        resp.raise_for_status()
        data = resp.json()
        return data.get("id", "unknown")

async def sync_event_to_providers(event_id: int):
    async with SessionLocal() as session:
        event = await session.get(Event, event_id)
        if not event:
            return

        for provider in config.external_providers:
            try:
                external_id = await push_to_provider(event, provider)
                await record_sync(session, event.id, provider.name, external_id)
                print(f"[OK] Synced event {event.id} → {provider.name}")
            except Exception as e:
                print(f"[FAIL] Sync to {provider.name} failed: {e}")

# ---------- API ----------
