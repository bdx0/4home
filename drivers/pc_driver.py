"""
PC driver — bật (WoL), tắt (SSH), kiểm tra trạng thái (ping).

Config trong devices.yaml:
  driver: pc
  config:
    ip: "192.168.1.x"
    mac: "aa:bb:cc:dd:ee:ff"      # dùng cho Wake-on-LAN
    ssh_user: "dd"                 # optional, để tắt qua SSH
    ssh_key: "~/.ssh/id_ed25519"  # optional
    broadcast: "192.168.1.255"    # WoL broadcast address
"""

import asyncio
import socket
import struct
from typing import Callable, Awaitable

from core.base_driver import BaseDriver


class PCDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._ip = config["ip"]
        self._mac = config.get("mac", "")
        self._ssh_user = config.get("ssh_user", "")
        self._ssh_key = config.get("ssh_key", "~/.ssh/id_ed25519")
        self._broadcast = config.get("broadcast", "192.168.1.255")

    async def connect(self) -> bool:
        return True  # Không cần persistent connection

    async def disconnect(self):
        pass

    async def get_state(self) -> dict:
        online = await self._ping()
        return {"on": online}

    async def set_state(self, state: dict) -> bool:
        if "on" not in state:
            return False
        if state["on"]:
            return await self._wake_on_lan()
        else:
            return await self._shutdown()

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        pass

    async def _ping(self) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "1", self._ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0

    async def _wake_on_lan(self) -> bool:
        if not self._mac:
            print(f"[{self.device_id}] No MAC address configured for WoL")
            return False
        try:
            mac_bytes = bytes.fromhex(self._mac.replace(":", "").replace("-", ""))
            magic = b"\xff" * 6 + mac_bytes * 16
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic, (self._broadcast, 9))
            sock.close()
            print(f"[{self.device_id}] WoL packet sent to {self._mac}")
            return True
        except Exception as e:
            print(f"[{self.device_id}] WoL error: {e}")
            return False

    async def _shutdown(self) -> bool:
        if not self._ssh_user:
            print(f"[{self.device_id}] No SSH user configured for shutdown")
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-i", self._ssh_key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                f"{self._ssh_user}@{self._ip}",
                "sudo", "shutdown", "-h", "now",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception as e:
            print(f"[{self.device_id}] SSH shutdown error: {e}")
            return False
