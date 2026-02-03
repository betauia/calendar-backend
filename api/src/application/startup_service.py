from src.application import client_service


def _push_events():
    pass

def startup():
    clientConfig = client_service.get_all_clients()
    for client in clientConfig.integrations:
        print(f"Loaded client: {client.name} at {client.baseUrl}")
    
if __name__ == "__main__":
    startup()