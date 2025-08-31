# app/domains/economy/__init__.py
from importlib import import_module

def __getattr__(name: str):
    if name == "router":
        return import_module(".api", __name__).router
    if name == "register_event_handlers":
        return import_module(".events", __name__).register_event_handlers
    if name == "service":         # ADD
        return import_module(".service", __name__)
    if name == "ton_service":     # (optional) keeps symmetry with main
        return import_module(".ton_service", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
