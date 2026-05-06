from src.infrastructure import client_config_repo


def get_all_clients():
    return client_config_repo.load_clients_from_config("config/appsettings.json")

def push_event_to_client(event, client):
    pass