from . import api, events, models, service
try:
    from .ws import ws_router  # new websocket router without inherited deps
except Exception:  # pragma: no cover
    ws_router = None

router = api.router
register_event_handlers = events.register_event_handlers
