def push_all_events(events, clients):
    for event in events:
        for client in clients:
            client.send_events(event)