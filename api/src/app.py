import asyncio
import discord
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel



intents = discord.Intents.default()
bot = discord.Client(intents=intents)

app = FastAPI()

bot_ready = asyncio.Event()


class SendMessage(BaseModel):
    content: str


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot_ready.set()


@app.post("/send")
async def send_message(cmd: SendMessage):
    # Ensure bot is ready
    if not bot_ready.is_set():
        raise HTTPException(status_code=503, detail="Bot not ready")

    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    await channel.send(cmd.content)
    return {"status": "sent"}
