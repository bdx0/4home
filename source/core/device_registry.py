import asyncio
import importlib
import os
import re

import yaml
from dotenv import load_dotenv

from core.base_driver import BaseDriver

load_dotenv()

DRIVER_MAP = {
    "tuya": "drivers.tuya_driver.TuyaDriver",
    "broadlink": "drivers.broadlink_driver.BroadlinkDriver",
    "xiaomi_ble": "drivers.xiaomi_ble_driver.XiaomiBLEDriver",
    "esphome": "drivers.esphome_driver.ESPHomeDriver",
    "miio": "drivers.miio_driver.MiioDriver",
    "pc": "drivers.pc_driver.PCDriver",
    "frigate": "drivers.frigate_driver.FrigateDriver",
}


def _expand_env(obj):
    """Thay thế ${VAR} trong config bằng giá trị env."""
    if isinstance(obj, str):
        return re.sub(r"\$\{(\w+)\}", lambda m: os.getenv(m.group(1), m.group(0)), obj)
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(i) for i in obj]
    return obj


class DeviceRegistry:
    def __init__(self, config_path: str = "config/devices.yaml"):
        self._drivers: dict[str, BaseDriver] = {}
        self._config_path = config_path

    def load(self):
        with open(self._config_path) as f:
            data = yaml.safe_load(f)
        for device in data.get("devices", []):
            driver_name = device["driver"]
            if driver_name not in DRIVER_MAP:
                print(f"[registry] Unknown driver: {driver_name}, skipping {device['id']}")
                continue
            module_path, class_name = DRIVER_MAP[driver_name].rsplit(".", 1)
            cls = getattr(importlib.import_module(module_path), class_name)
            config = _expand_env(device.get("config", {}))
            config["_name"] = device.get("name", device["id"])
            config["_type"] = device.get("type", "unknown")
            self._drivers[device["id"]] = cls(device["id"], config)
        print(f"[registry] Loaded {len(self._drivers)} devices")

    async def connect_all(self):
        results = await asyncio.gather(
            *[d.connect() for d in self._drivers.values()],
            return_exceptions=True,
        )
        for device_id, result in zip(self._drivers, results):
            if isinstance(result, Exception):
                print(f"[registry] {device_id} connect error: {result}")
            elif not result:
                print(f"[registry] {device_id} failed to connect")

    async def disconnect_all(self):
        await asyncio.gather(*[d.disconnect() for d in self._drivers.values()])

    def get(self, device_id: str) -> BaseDriver | None:
        return self._drivers.get(device_id)

    def find(self, pattern: str) -> list[BaseDriver]:
        """Wildcard lookup, e.g. 'sensor.*' hoặc '*.bedroom'."""
        regex = re.compile("^" + pattern.replace(".", r"\.").replace("*", ".*") + "$")
        return [d for did, d in self._drivers.items() if regex.match(did)]

    def all(self) -> dict[str, BaseDriver]:
        return self._drivers
