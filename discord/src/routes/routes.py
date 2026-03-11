import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
import discord
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()  # loads .env file into os.environ

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
intents.guild_scheduled_events = True

bot = discord.Client(intents=intents)
app = FastAPI()

bot_ready = asyncio.Event()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot_ready.set()


@app.get("/events")
async def list_scheduled_events():
    if not bot_ready.is_set():
        raise HTTPException(status_code=503, detail="Bot not ready")

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        guild = await bot.fetch_guild(GUILD_ID)

    events = await guild.fetch_scheduled_events()

    return [
        {
            "discord_event_id": e.id,
            "name": e.name,
            "description": e.description,
            "status": str(e.status),
            "entity_type": str(e.entity_type),
            "channel_id": e.channel_id,
            "location": e.location,
        }
        for e in events
    ]

class EventCreateDTO(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime


@app.post("/events")
async def create_scheduled_event(dto: EventCreateDTO):
    if not bot_ready.is_set():
        raise HTTPException(status_code=503, detail="Bot not ready")

    # Fetch the guild
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        guild = await bot.fetch_guild(GUILD_ID)

    try:
        # Create a scheduled event on Discord
        event = await guild.create_scheduled_event(
            name=dto.title,
            start_time=dto.start_time.astimezone(),  # ensure timezone-aware
            end_time=dto.end_time.astimezone(),
            entity_type=discord.EntityType.external,  # or voice stage/channel
            privacy_level=discord.PrivacyLevel.guild_only,
            location="Online"  # required for external events
        )
    except discord.HTTPException as e:
        raise HTTPException(status_code=400, detail=f"Failed to create event: {e}")

    return {
        "discord_event_id": event.id,
        "name": event.name,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "status": str(event.status),
        "entity_type": str(event.entity_type),
        "location": event.location,
    }