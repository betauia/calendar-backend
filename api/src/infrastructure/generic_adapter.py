# infrastructure/providers/generic_adapter.py
import httpx

class GenericProviderAdapter:
    def __init__(self, url: str):
        self.url = url

    async def push_event(self, event):
        """
        Sends the event to the provider API according to your protocol.
        Returns the provider's external event ID on success.
        """
        async with httpx.AsyncClient(base_url=str(self.url)) as client:
            resp = await client.post("/events", json={
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
            })
            resp.raise_for_status()
            data = resp.json()
            return data["id"]
