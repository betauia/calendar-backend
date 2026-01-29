def get_all_events(event_repository: EventRepository) -> list[Event]:
    return event_repository.list_all()