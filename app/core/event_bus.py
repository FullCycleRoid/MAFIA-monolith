import asyncio
from typing import Any, Callable, Dict, List

from app.shared.utils import logger


class EventBus:
    def __init__(self):
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.log = logger.get_logger("event_bus")

    async def publish(self, event_name: str, event_data: Any):
        if event_name in self.subscriptions:
            tasks = []
            for handler in self.subscriptions[event_name]:
                tasks.append(self._run_handler(handler, event_data))
            await asyncio.gather(*tasks)

    async def _run_handler(self, handler: Callable, event_data: Any):
        try:
            # Добавить таймаут
            await asyncio.wait_for(
                handler(event_data)
                if asyncio.iscoroutinefunction(handler)
                else asyncio.to_thread(handler, event_data),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            self.log.error(f"Handler timed out: {handler.__name__}")
        except Exception as e:
            self.log.error(f"Error in event handler: {e}")

    def subscribe(self, event_name: str, handler: Callable[[Any], None]):
        if event_name not in self.subscriptions:
            self.subscriptions[event_name] = []
        self.subscriptions[event_name].append(handler)
        self.log.debug(f"Subscribed handler to: {event_name}")


# Глобальный экземпляр шины событий
event_bus = EventBus()


def init_event_bus():
    # Инициализация шины событий
    pass
