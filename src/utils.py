from pydantic import BaseModel
from typing import Callable, Any, Optional, Union

class JWT(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[Union[str, int]] = None


class Decorators:

    @staticmethod
    def ensure_session(method: Callable) -> Callable:
        def wrapper(client, *args, **kwargs) -> Optional[Any]:
            if client.session == None:
                raise ConnectionError(f"""
                    Start a session with self.start_session() before of make a 
                    request or use "with" expression like with 
                    {client.__class__.__name__}(url=...) as client: ...
                """)
            return method(client, *args, **kwargs)
        return wrapper

    @staticmethod
    def ensure_connection(method: Callable) -> Callable:
        def wrapper(client, *args, **kwargs) -> Optional[Any]:
            if not client.is_connected:
                raise ConnectionError("Client is now disconnected.")
            return method(client, *args, **kwargs)
        return wrapper
