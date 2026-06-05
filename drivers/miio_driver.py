"""
Xiaomi Miio driver — điều khiển thiết bị Xiaomi qua local network.
Hỗ trợ: Air Purifier, Fan, Robot Vacuum, v.v.

Cần lấy token từ app Xiaomi trước (xem README).

Config trong devices.yaml:
  driver: miio
  config:
    ip: "192.168.1.x"
    token: "${MIIO_PURIFIER_TOKEN}"   # 32 ký tự hex
    model: "zhimi.airpurifier.mb3"    # optional, để auto-detect properties
"""

import asyncio
from typing import Callable, Awaitable

import miio

from core.base_driver import BaseDriver

# Map model → class trong python-miio
_MODEL_CLASS = {
    "zhimi.airpurifier": miio.AirPurifier,
    "zhimi.airpurifier.mb3": miio.AirPurifierMiot,
    "zhimi.airpurifier.ma4": miio.AirPurifier,
    "dmaker.airpurifier": miio.AirPurifierMiot,
}


class MiioDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._ip = config["ip"]
        self._token = config["token"]
        self._model = config.get("model", "")
        self._device = None

    async def connect(self) -> bool:
        try:
            cls = self._pick_class()
            self._device = cls(self._ip, self._token)
            # Test connection
            await asyncio.to_thread(self._device.status)
            print(f"[{self.device_id}] Miio connected: {self._ip}")
            return True
        except Exception as e:
            print(f"[{self.device_id}] Miio connect error: {e}")
            return False

    async def disconnect(self):
        self._device = None

    async def get_state(self) -> dict:
        try:
            status = await asyncio.to_thread(self._device.status)
            return self._parse_status(status)
        except Exception as e:
            print(f"[{self.device_id}] get_state error: {e}")
            return {}

    async def set_state(self, state: dict) -> bool:
        if not self._device:
            return False
        try:
            if "on" in state:
                fn = self._device.on if state["on"] else self._device.off
                await asyncio.to_thread(fn)
            if "mode" in state:
                mode_map = {"auto": "Auto", "sleep": "Silent", "fan": "Favorite", "high": "High"}
                await asyncio.to_thread(self._device.set_mode, mode_map.get(state["mode"], state["mode"]))
            if "fan_speed" in state:
                await asyncio.to_thread(self._device.set_favorite_level, state["fan_speed"])
            return True
        except Exception as e:
            print(f"[{self.device_id}] set_state error: {e}")
            return False

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        pass  # Miio không hỗ trợ push, cần poll

    def _pick_class(self):
        for prefix, cls in _MODEL_CLASS.items():
            if self._model.startswith(prefix):
                return cls
        return miio.AirPurifier  # fallback

    def _parse_status(self, status) -> dict:
        state = {}
        try:
            state["on"] = status.is_on
        except Exception:
            pass
        try:
            state["mode"] = str(status.mode).lower()
        except Exception:
            pass
        try:
            state["aqi"] = status.aqi  # PM2.5
        except Exception:
            pass
        try:
            state["filter_pct"] = status.filter_life_remaining
        except Exception:
            pass
        try:
            state["humidity"] = status.humidity
        except Exception:
            pass
        try:
            state["temperature"] = status.temperature
        except Exception:
            pass
        try:
            state["fan_speed"] = status.favorite_level
        except Exception:
            pass
        return state
