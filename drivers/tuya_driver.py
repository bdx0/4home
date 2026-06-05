"""
Tuya Local driver — điều khiển đèn và thiết bị Tuya qua local network.

Không qua cloud, dùng tinytuya để giao tiếp trực tiếp.
Cần lấy device_id và local_key từ Tuya IoT Platform (xem README).

Config trong devices.yaml:
  driver: tuya
  config:
    device_id: "abc123..."       # Device ID từ Tuya app
    local_key: "${TUYA_KEY_X}"   # Local key từ Tuya IoT Platform
    ip: "192.168.1.x"
    version: "3.3"               # hoặc 3.1, 3.4 tùy firmware
    type: light                  # light | switch | dimmer
"""

import asyncio
from typing import Callable, Awaitable

import tinytuya

from core.base_driver import BaseDriver


class TuyaDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._tuya_id = config["device_id"]
        self._local_key = config["local_key"]
        self._ip = config["ip"]
        self._version = float(config.get("version", "3.3"))
        self._device_type = config.get("type", "light")
        self._device = None
        self._dps_map = self._build_dps_map()

    async def connect(self) -> bool:
        try:
            self._device = tinytuya.BulbDevice(
                dev_id=self._tuya_id,
                address=self._ip,
                local_key=self._local_key,
                version=self._version,
            )
            self._device.set_socketPersistent(True)
            status = await asyncio.to_thread(self._device.status)
            if "Error" in status:
                print(f"[{self.device_id}] Tuya error: {status['Error']}")
                return False
            print(f"[{self.device_id}] Tuya connected: {self._ip}")
            return True
        except Exception as e:
            print(f"[{self.device_id}] Tuya connect error: {e}")
            return False

    async def disconnect(self):
        if self._device:
            try:
                self._device.close()
            except Exception:
                pass

    async def get_state(self) -> dict:
        try:
            raw = await asyncio.to_thread(self._device.status)
            return self._parse_dps(raw.get("dps", {}))
        except Exception as e:
            print(f"[{self.device_id}] get_state error: {e}")
            return {}

    async def set_state(self, state: dict) -> bool:
        if not self._device:
            return False
        try:
            dps = self._state_to_dps(state)
            if dps:
                await asyncio.to_thread(self._device.set_multiple_values, dps)
            return True
        except Exception as e:
            print(f"[{self.device_id}] set_state error: {e}")
            return False

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        pass  # Tuya local không hỗ trợ push, cần poll

    def _build_dps_map(self) -> dict:
        # DPS keys chuẩn cho Tuya bulb/dimmer
        # Có thể override trong config nếu thiết bị dùng DPS khác
        return self.config.get("dps_map", {
            "1": "on",           # bool
            "2": "mode",         # "white" | "colour" | "scene" | "music"
            "3": "brightness",   # 10-1000 (Tuya) → 0-100 (schema)
            "4": "color_temp",   # 0-1000 (Tuya, warm→cool) → kelvin
            "5": "rgb",          # hex string "00ff00" hoặc hsv
        })

    def _parse_dps(self, dps: dict) -> dict:
        state = {}
        reverse = {v: k for k, v in self._dps_map.items()}

        on_key = reverse.get("on", "1")
        if on_key in dps:
            state["on"] = bool(dps[on_key])

        bright_key = reverse.get("brightness", "3")
        if bright_key in dps:
            # Tuya brightness: 10-1000 → schema: 0-100
            raw = int(dps[bright_key])
            state["brightness"] = max(0, min(100, round((raw - 10) / 990 * 100)))

        temp_key = reverse.get("color_temp", "4")
        if temp_key in dps:
            # Tuya color_temp: 0=warm(2700K) → 1000=cool(6500K)
            raw = int(dps[temp_key])
            state["color_temp"] = round(2700 + raw / 1000 * (6500 - 2700))

        rgb_key = reverse.get("rgb", "5")
        if rgb_key in dps and dps[rgb_key]:
            state["rgb"] = self._parse_rgb(dps[rgb_key])

        return state

    def _state_to_dps(self, state: dict) -> dict:
        reverse = {v: k for k, v in self._dps_map.items()}
        dps = {}

        if "on" in state:
            dps[reverse.get("on", "1")] = bool(state["on"])

        if "brightness" in state:
            # schema: 0-100 → Tuya: 10-1000
            raw = round(state["brightness"] / 100 * 990 + 10)
            dps[reverse.get("brightness", "3")] = max(10, min(1000, raw))

        if "color_temp" in state:
            # kelvin → Tuya 0-1000
            k = state["color_temp"]
            raw = round((k - 2700) / (6500 - 2700) * 1000)
            dps[reverse.get("color_temp", "4")] = max(0, min(1000, raw))
            dps[reverse.get("mode", "2")] = "white"

        if "rgb" in state:
            r, g, b = state["rgb"]
            dps[reverse.get("rgb", "5")] = f"{r:02x}{g:02x}{b:02x}0000ff"
            dps[reverse.get("mode", "2")] = "colour"

        return dps

    def _parse_rgb(self, raw: str) -> list[int]:
        try:
            # Tuya colour format: rrggbbhhhhsssvvv
            r = int(raw[0:2], 16)
            g = int(raw[2:4], 16)
            b = int(raw[4:6], 16)
            return [r, g, b]
        except Exception:
            return [255, 255, 255]
