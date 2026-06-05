"""
Broadlink IR driver — điều khiển thiết bị qua IR blaster (RM4 mini/pro).

IR là one-way: không đọc được state thực từ thiết bị.
State được cache lại từ lần set_state() gần nhất.

Config trong devices.yaml:
  driver: broadlink
  config:
    ip: "192.168.1.x"
    mac: "aa:bb:cc:dd:ee:ff"   # optional, dùng để identify khi discover
    codes:
      on: "JgBYAAABKpIV..."     # base64 hoặc hex
      off: "JgBYAAABKpIV..."
      temp_24: "JgBYABCD..."
      # thêm các code khác tại đây
"""

import asyncio
import base64
from typing import Callable, Awaitable

import broadlink

from core.base_driver import BaseDriver


class BroadlinkDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._rm = None
        self._codes: dict[str, str] = config.get("codes", {})
        self._cached_state: dict = {}

    async def connect(self) -> bool:
        try:
            devices = await asyncio.to_thread(broadlink.discover, timeout=5)
            target_ip = self.config.get("ip")
            target_mac = self.config.get("mac", "").lower().replace(":", "")

            for dev in devices:
                ip_match = target_ip and dev.host[0] == target_ip
                mac_match = target_mac and dev.mac.hex() == target_mac
                if ip_match or mac_match:
                    self._rm = dev
                    await asyncio.to_thread(self._rm.auth)
                    print(f"[{self.device_id}] Connected to Broadlink {dev.host[0]}")
                    return True

            print(f"[{self.device_id}] Broadlink device not found")
            return False
        except Exception as e:
            print(f"[{self.device_id}] Connect error: {e}")
            return False

    async def disconnect(self):
        self._rm = None

    async def get_state(self) -> dict:
        # IR one-way: trả về cached state
        return self._cached_state.copy()

    async def set_state(self, state: dict) -> bool:
        if not self._rm:
            return False
        code_keys = self._state_to_code_keys(state)
        for key in code_keys:
            if key not in self._codes:
                print(f"[{self.device_id}] No IR code for: '{key}'. Available: {list(self._codes)}")
                return False
            raw = self._decode_code(self._codes[key])
            await asyncio.to_thread(self._rm.send_data, raw)
            await asyncio.sleep(0.3)
        self._cached_state.update(state)
        return True

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        pass  # IR không hỗ trợ push

    def _decode_code(self, code: str) -> bytes:
        code = code.strip()
        try:
            # Thử base64 trước (Broadlink format: JgBY...)
            return base64.b64decode(code)
        except Exception:
            # Fallback sang hex
            return bytes.fromhex(code)

    def _state_to_code_keys(self, state: dict) -> list[str]:
        """Map state dict → danh sách IR code keys cần gửi theo thứ tự."""
        keys = []
        if "on" in state:
            keys.append("on" if state["on"] else "off")
        if "temp" in state:
            keys.append(f"temp_{int(state['temp'])}")
        if "mode" in state:
            keys.append(f"mode_{state['mode']}")
        if "fan" in state:
            keys.append(f"fan_{state['fan']}")
        return keys

    async def learn_code(self, code_name: str) -> str | None:
        """Học IR code mới. Dùng khi setup."""
        if not self._rm:
            print("Not connected")
            return None
        print(f"Press the button on your remote for '{code_name}'...")
        self._rm.enter_learning()
        await asyncio.sleep(4)
        code = self._rm.check_data()
        if code:
            b64 = base64.b64encode(code).decode()
            print(f"Learned code for '{code_name}': {b64}")
            return b64
        print("No code received")
        return None
