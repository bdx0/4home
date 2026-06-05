"""
Xiaomi BLE sensor driver — LYWSD03MMC (nhiệt độ + độ ẩm).

Sensor broadcast passive advertisements, không cần kết nối trực tiếp.
Dùng thư viện `bleak` để scan BLE.

Có 2 chế độ:
  - passive: scan advertisement liên tục (mặc định, không tốn pin sensor)
  - active: kết nối và đọc GATT characteristic (cần firmware ATC để không cần auth)

Config trong devices.yaml:
  driver: xiaomi_ble
  config:
    mac: "A4:C1:38:xx:xx:xx"
    mode: passive   # hoặc active
    poll_interval: 60   # giây, chỉ dùng ở mode active
"""

import asyncio
import struct
from typing import Callable, Awaitable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from core.base_driver import BaseDriver

# UUID cho LYWSD03MMC
_TEMP_HUMIDITY_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"


class XiaomiBLEDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._mac = config["mac"].upper()
        self._mode = config.get("mode", "passive")
        self._poll_interval = config.get("poll_interval", 60)
        self._state: dict = {}
        self._callbacks: list[Callable] = []
        self._scan_task: asyncio.Task | None = None
        self._scanner: BleakScanner | None = None

    async def connect(self) -> bool:
        if self._mode == "passive":
            self._scanner = BleakScanner(detection_callback=self._on_advertisement)
            await self._scanner.start()
            self._scan_task = asyncio.create_task(self._passive_loop())
            print(f"[{self.device_id}] BLE passive scan started for {self._mac}")
            return True
        else:
            # Active mode: thử kết nối một lần để verify
            try:
                async with BleakClient(self._mac, timeout=10) as client:
                    if client.is_connected:
                        self._scan_task = asyncio.create_task(self._active_loop())
                        return True
            except Exception as e:
                print(f"[{self.device_id}] BLE connect error: {e}")
            return False

    async def disconnect(self):
        if self._scan_task:
            self._scan_task.cancel()
        if self._scanner:
            await self._scanner.stop()

    async def get_state(self) -> dict:
        return self._state.copy()

    async def set_state(self, state: dict) -> bool:
        # Sensor không hỗ trợ set state
        return False

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        self._callbacks.append(callback)

    def _on_advertisement(self, device: BLEDevice, adv: AdvertisementData):
        if device.address.upper() != self._mac:
            return
        # Parse Xiaomi MiBeacon advertisement data
        mfr_data = adv.manufacturer_data
        if not mfr_data:
            return
        for company_id, data in mfr_data.items():
            if company_id == 0x0157 and len(data) >= 14:  # Xiaomi
                self._parse_mibeacon(data)

    def _parse_mibeacon(self, data: bytes):
        # LYWSD03MMC MiBeacon format
        try:
            obj_type = struct.unpack_from("<H", data, 11)[0]
            obj_len = data[13]
            obj_data = data[14:14 + obj_len]

            if obj_type == 0x1004 and obj_len == 2:  # Temperature
                temp = struct.unpack_from("<h", obj_data)[0] / 10
                self._state["temperature"] = temp
                asyncio.get_event_loop().create_task(self._notify())
            elif obj_type == 0x1006 and obj_len == 1:  # Humidity
                humidity = obj_data[0]
                self._state["humidity"] = humidity
                asyncio.get_event_loop().create_task(self._notify())
            elif obj_type == 0x100A and obj_len == 1:  # Battery
                self._state["battery_pct"] = obj_data[0]
        except Exception:
            pass

    async def _passive_loop(self):
        """Giữ scanner chạy liên tục."""
        while True:
            await asyncio.sleep(60)

    async def _active_loop(self):
        """Poll định kỳ qua GATT connection."""
        while True:
            try:
                async with BleakClient(self._mac, timeout=10) as client:
                    data = await client.read_gatt_char(_TEMP_HUMIDITY_UUID)
                    temp = struct.unpack_from("<h", data, 0)[0] / 100
                    humidity = data[2]
                    battery = data[3]
                    self._state = {
                        "temperature": temp,
                        "humidity": humidity,
                        "battery_pct": battery,
                    }
                    await self._notify()
            except Exception as e:
                print(f"[{self.device_id}] BLE read error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def _notify(self):
        for cb in self._callbacks:
            await cb(self._state.copy())
