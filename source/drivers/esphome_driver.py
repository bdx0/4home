"""
ESPHome driver — giao tiếp với ESP32 chạy ESPHome qua Native API.

Dùng thư viện `aioesphomeapi` (nhanh hơn MQTT, không cần broker).
Tự động subscribe tất cả entities và map sang state schema.

Config trong devices.yaml:
  driver: esphome
  config:
    host: "192.168.1.x"    # IP của ESP32
    port: 6053              # default ESPHome API port
    password: ""            # ESPHome API password (nếu có)
    entities:               # map ESPHome entity key → state field
      switch_relay: on
      sensor_temperature: temperature
      sensor_humidity: humidity
"""

import asyncio
from typing import Callable, Awaitable

import aioesphomeapi

from core.base_driver import BaseDriver


class ESPHomeDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._host = config["host"]
        self._port = config.get("port", 6053)
        self._password = config.get("password", "")
        self._entity_map: dict[str, str] = config.get("entities", {})
        self._state: dict = {}
        self._callbacks: list[Callable] = []
        self._client: aioesphomeapi.APIClient | None = None
        self._reconnect_task: asyncio.Task | None = None

    async def connect(self) -> bool:
        try:
            self._client = aioesphomeapi.APIClient(
                self._host, self._port, self._password
            )
            await self._client.connect(login=True)
            entities, services = await self._client.list_entities_services()
            self._key_to_name = {e.key: e.name for e in entities}

            self._client.subscribe_states(self._on_state_change)
            print(f"[{self.device_id}] ESPHome connected: {self._host}, {len(entities)} entities")
            return True
        except Exception as e:
            print(f"[{self.device_id}] ESPHome connect error: {e}")
            return False

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()

    async def get_state(self) -> dict:
        return self._state.copy()

    async def set_state(self, state: dict) -> bool:
        if not self._client:
            return False
        try:
            # Map state fields → ESPHome service calls
            for field, value in state.items():
                entity_key = self._find_entity_key(field)
                if entity_key is None:
                    continue
                if field == "on":
                    await self._client.switch_command(entity_key, value)
                elif field == "brightness":
                    await self._client.light_command(
                        entity_key, brightness=int(value / 100 * 255)
                    )
            return True
        except Exception as e:
            print(f"[{self.device_id}] set_state error: {e}")
            return False

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        self._callbacks.append(callback)

    def _on_state_change(self, state):
        entity_name = self._key_to_name.get(state.key, "")
        # Map ESPHome entity name → state field via entity_map config
        for esphome_key, state_field in self._entity_map.items():
            if esphome_key in entity_name.lower().replace(" ", "_"):
                if hasattr(state, "state"):
                    self._state[state_field] = state.state
                break
        for cb in self._callbacks:
            asyncio.get_event_loop().create_task(cb(self._state.copy()))

    def _find_entity_key(self, field: str) -> int | None:
        for esphome_key, state_field in self._entity_map.items():
            if state_field == field:
                for key, name in self._key_to_name.items():
                    if esphome_key in name.lower().replace(" ", "_"):
                        return key
        return None
