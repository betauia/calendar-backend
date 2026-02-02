from application import client_service


def _push_events():
    pass

def startup():
    clients = client_service.get_all_clients()
    