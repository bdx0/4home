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
        """Lấy trạng thái camera từ Frigate.

        Frigate exposes per-camera runtime stats via `/api/stats` under
        `cameras.<camera_name>`; `/api/<camera>/stats` returns 404 on Frigate
        0.15.x.
        """
        if self._session is None:
            return {}

        try:
            async with self._session.get(f"{self._base_url}/api/stats") as r:
                if r.status != 200:
                    return {}
                data = await r.json()

            camera_stats = data.get("cameras", {}).get(self._camera, {})
            if not camera_stats:
                return {}

            recording = False
            try:
                async with self._session.get(f"{self._base_url}/api/config") as r:
                    if r.status == 200:
                        config = await r.json()
                        camera_config = config.get("cameras", {}).get(self._camera, {})
                        recording = bool(
                            camera_config.get("record", {}).get("enabled", False)
                        )
            except Exception:
                # Runtime stats are still useful even if config is unavailable.
                pass

            camera_fps = camera_stats.get("camera_fps", 0) or 0
            process_fps = camera_stats.get("process_fps", 0) or 0
            return {
                "streaming": bool(camera_fps or process_fps),
                "recording": recording,
                "rtsp_url": f"{self._base_url}/live/webrtc/api/ws?src={self._camera}",
                "fps": camera_fps,
                "detection_fps": camera_stats.get("detection_fps", 0),
                "detection": bool(camera_stats.get("detection_enabled", False)),
            }
        except Exception as e:
            print(f"[{self.device_id}] get_state error: {e}")
            return {}

    async def set_state(self, state: dict) -> bool:
        # Current Frigate API discovery did not expose safe recording/detection
        # mutation endpoints. Avoid pretending a state change succeeded.
        print(f"[{self.device_id}] set_state unsupported for Frigate camera: {state}")
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
