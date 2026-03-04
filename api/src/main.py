from fastapi import FastAPI
from routes import events
from domain.models import Base
from infrastructure.session import engine

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}})


app.include_router(events.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
