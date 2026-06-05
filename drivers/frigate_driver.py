"""
Frigate camera driver — tích hợp với Frigate NVR.

Frigate đang chạy tại: https://frigate.nix01.bdx0.io.vn
Cameras: san, wife, c6n, yo1, yo2, yo4

Config trong devices.yaml:
  driver: frigate
  config:
    base_url: "${FRIGATE_URL}"       # https://frigate.nix01.bdx0.io.vn
    camera: "san"                    # tên camera trong Frigate
    api_key: "${FRIGATE_API_KEY}"    # optional nếu có auth
"""

import asyncio
from typing import Callable, Awaitable

import aiohttp

from core.base_driver import BaseDriver


class FrigateDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._base_url = config["base_url"].rstrip("/")
        self._camera = config["camera"]
        self._api_key = config.get("api_key", "")
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        self._session = aiohttp.ClientSession(headers=headers)
        try:
            async with self._session.get(f"{self._base_url}/api/version") as r:
                ok = r.status == 200
                if ok:
                    print(f"[{self.device_id}] Frigate connected: {self._camera}")
                return ok
        except Exception as e:
            print(f"[{self.device_id}] Frigate connect error: {e}")
            return False

    async def disconnect(self):
        if self._session:
            await self._session.close()

    async def get_state(self) -> dict:
        try:
            async with self._session.get(
                f"{self._base_url}/api/{self._camera}/stats"
            ) as r:
                if r.status != 200:
                    return {}
                data = await r.json()
                return {
                    "streaming": True,
                    "recording": data.get("record", {}).get("enabled", False),
                    "rtsp_url": f"{self._base_url}/live/webrtc/api/ws?src={self._camera}",
                    "fps": data.get("camera_fps", 0),
                    "detection_fps": data.get("detection_fps", 0),
                }
        except Exception as e:
            print(f"[{self.device_id}] get_state error: {e}")
            return {}

    async def set_state(self, state: dict) -> bool:
        # Frigate hỗ trợ bật/tắt recording và detection
        try:
            if "recording" in state:
                await self._session.post(
                    f"{self._base_url}/api/{self._camera}/recordings/toggle"
                )
            if "detection" in state:
                await self._session.post(
                    f"{self._base_url}/api/{self._camera}/detect/toggle"
                )
            return True
        except Exception as e:
            print(f"[{self.device_id}] set_state error: {e}")
            return False

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        pass

    async def get_snapshot(self) -> bytes | None:
        """Lấy ảnh snapshot hiện tại."""
        try:
            async with self._session.get(
                f"{self._base_url}/api/{self._camera}/latest.jpg"
            ) as r:
                if r.status == 200:
                    return await r.read()
        except Exception:
            pass
        return None

    async def get_events(self, limit: int = 10) -> list[dict]:
        """Lấy danh sách events gần nhất."""
        try:
            async with self._session.get(
                f"{self._base_url}/api/events",
                params={"camera": self._camera, "limit": limit},
            ) as r:
                if r.status == 200:
                    return await r.json()
        except Exception:
            pass
        return []
