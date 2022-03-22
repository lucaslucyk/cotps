from typing import Callable, Any, Optional


class Decorators:
    @staticmethod
    def ensure_connection(method: Callable) -> Callable:
        def wrapper(client, *args, **kwargs) -> Optional[Any]:
            if not client.is_connected:
                raise ConnectionError("Client is now disconnected.")
            return method(client, *args, **kwargs)
        return wrapper
