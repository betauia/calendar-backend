import asyncio
import uvicorn
from routes.routes import bot, DISCORD_TOKEN, app


async def main():
    await bot.login(str(DISCORD_TOKEN))

    # start discord gateway
    asyncio.create_task(bot.connect())

    # start fastapi
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
