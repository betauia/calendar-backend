import asyncio

def syncEventsFromBaseServer():
    events = event_service.getEvents()
    
    for event in events:
        event_service.createEvent(event)

if __name__ == "__main__":
    syncEventsFromBaseServer()