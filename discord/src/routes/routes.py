import asyncio
import discord
from fastapi import FastAPI, HTTPException
from datetime import timezone

DISCORD_TOKEN = ""
GUILD_ID = ""

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
