from abc import ABC, abstractmethod
from typing import Callable, Awaitable


class BaseDriver(ABC):
    def __init__(self, device_id: str, config: dict):
        self.device_id = device_id
        self.config = config

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def disconnect(self): ...

    @abstractmethod
    async def get_state(self) -> dict: ...

    @abstractmethod
    async def set_state(self, state: dict) -> bool: ...

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        pass
