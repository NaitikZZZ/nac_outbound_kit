from .. import hubspot_client


def run():
    """Read-only -- no write risk. Returns the three pickers' options; the UI
    adds an overall "skip associations" shortcut on top of these (each
    individually optional too)."""
    return {
        "projects": hubspot_client.list_projects(),
        "partners": hubspot_client.list_partners(),
        "events": hubspot_client.list_events(),
    }
