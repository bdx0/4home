# Driver Templates

Template sẵn cho từng giao thức. Copy và điều chỉnh cho thiết bị cụ thể.

## MQTT Driver

```python
import asyncio
import json
import paho.mqtt.client as mqtt
from core.base_driver import BaseDriver

class MQTTDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._client = mqtt.Client()
        self._state: dict = {}
        self._callbacks = []

    async def connect(self) -> bool:
        broker = self.config["broker"].replace("mqtt://", "")
        host, port = broker.split(":") if ":" in broker else (broker, 1883)
        self._client.on_message = self._on_message
        self._client.connect(host, int(port))
        self._client.subscribe(self.config["topic_state"])
        self._client.loop_start()
        return True

    async def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    async def get_state(self) -> dict:
        return self._state.copy()

    async def set_state(self, state: dict) -> bool:
        payload = json.dumps(self._build_command(state))
        result = self._client.publish(self.config["topic_set"], payload)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def _on_message(self, client, userdata, msg):
        try:
            raw = json.loads(msg.payload)
            self._state = self._parse_state(raw)
        except Exception as e:
            print(f"[{self.device_id}] parse error: {e}")

    def _parse_state(self, raw: dict) -> dict:
        # Customize: map raw MQTT payload → state schema
        # Zigbee2MQTT example:
        return {
            "on": raw.get("state", "OFF").upper() == "ON",
            "brightness": round(raw.get("brightness", 0) / 254 * 100),
            "color_temp": round(1_000_000 / raw["color_temp"]) if "color_temp" in raw else None,
            "rgb": [raw["color"]["r"], raw["color"]["g"], raw["color"]["b"]] if "color" in raw else None,
        }

    def _build_command(self, state: dict) -> dict:
        cmd = {}
        if "on" in state:
            cmd["state"] = "ON" if state["on"] else "OFF"
        if "brightness" in state:
            cmd["brightness"] = round(state["brightness"] / 100 * 254)
        if "color_temp" in state:
            cmd["color_temp"] = round(1_000_000 / state["color_temp"])
        if "rgb" in state:
            r, g, b = state["rgb"]
            cmd["color"] = {"r": r, "g": g, "b": b}
        return cmd
```

## HTTP Driver

```python
import aiohttp
from core.base_driver import BaseDriver

class HTTPDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        self._session = aiohttp.ClientSession(headers=self._build_headers())
        async with self._session.get(f"{self.config['base_url']}/status") as r:
            return r.status < 400

    async def disconnect(self):
        if self._session:
            await self._session.close()

    async def get_state(self) -> dict:
        async with self._session.get(f"{self.config['base_url']}/state") as r:
            return self._parse_state(await r.json())

    async def set_state(self, state: dict) -> bool:
        async with self._session.post(f"{self.config['base_url']}/control", json=self._build_command(state)) as r:
            return r.status == 200

    def _build_headers(self) -> dict:
        auth = self.config.get("auth", {})
        if auth.get("type") == "bearer":
            return {"Authorization": f"Bearer {auth['token']}"}
        return {}

    def _parse_state(self, raw: dict) -> dict:
        return raw  # Customize theo API cụ thể

    def _build_command(self, state: dict) -> dict:
        return state  # Customize theo API cụ thể
```

## Tuya Local Driver (tinytuya)

```python
import asyncio
import tinytuya
from core.base_driver import BaseDriver

class TuyaDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._device = None

    async def connect(self) -> bool:
        self._device = tinytuya.Device(
            dev_id=self.config["device_id"],
            address=self.config["ip"],
            local_key=self.config["local_key"],
            version=self.config.get("version", "3.3"),
        )
        status = await asyncio.to_thread(self._device.status)
        return status.get("Error") is None

    async def disconnect(self):
        pass

    async def get_state(self) -> dict:
        raw = await asyncio.to_thread(self._device.status)
        return self._parse_dps(raw.get("dps", {}))

    async def set_state(self, state: dict) -> bool:
        dps = self._state_to_dps(state)
        result = await asyncio.to_thread(self._device.set_multiple_values, dps)
        return result is not None

    def _parse_dps(self, dps: dict) -> dict:
        # Customize: map DPS keys → state schema
        # Tra cứu DPS keys từ app Tuya hoặc tinytuya wizard
        return {
            "on": dps.get("1", False),
            "brightness": round(int(dps.get("3", 0)) / 1000 * 100),  # Tuya: 0-1000
        }

    def _state_to_dps(self, state: dict) -> dict:
        dps = {}
        if "on" in state:
            dps["1"] = state["on"]
        if "brightness" in state:
            dps["3"] = round(state["brightness"] / 100 * 1000)
        return dps
```

## IR Driver (Broadlink RM4)

```python
import asyncio
import broadlink
from core.base_driver import BaseDriver

class IRDriver(BaseDriver):
    """
    IR là one-way: không đọc state thực từ thiết bị được.
    State được cache lại từ lần set_state() gần nhất.
    """

    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._rm = None
        self._codes: dict = config.get("codes", {})
        self._cached_state: dict = {}

    async def connect(self) -> bool:
        devices = await asyncio.to_thread(broadlink.discover, timeout=5)
        for dev in devices:
            if dev.host[0] == self.config["ip"]:
                self._rm = dev
                await asyncio.to_thread(self._rm.auth)
                return True
        return False

    async def disconnect(self):
        pass

    async def get_state(self) -> dict:
        return self._cached_state.copy()

    async def set_state(self, state: dict) -> bool:
        for code_key in self._state_to_code_keys(state):
            if code_key not in self._codes:
                raise ValueError(f"Không có IR code cho: {code_key}")
            raw = bytes.fromhex(self._codes[code_key])
            await asyncio.to_thread(self._rm.send_data, raw)
            await asyncio.sleep(0.3)
        self._cached_state.update(state)
        return True

    def _state_to_code_keys(self, state: dict) -> list[str]:
        keys = []
        if "on" in state:
            keys.append("on" if state["on"] else "off")
        if "temp" in state:
            keys.append(f"temp_{int(state['temp'])}")
        if "mode" in state:
            keys.append(f"mode_{state['mode']}")
        return keys
```

## WebSocket Driver

```python
import asyncio
import json
import websockets
from core.base_driver import BaseDriver

class WebSocketDriver(BaseDriver):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._ws = None
        self._state: dict = {}
        self._listen_task = None

    async def connect(self) -> bool:
        self._ws = await websockets.connect(self.config["url"])
        self._listen_task = asyncio.create_task(self._listen())
        return True

    async def disconnect(self):
        if self._listen_task:
            self._listen_task.cancel()
        if self._ws:
            await self._ws.close()

    async def get_state(self) -> dict:
        await self._ws.send(json.dumps({"type": "get_state", "id": self.device_id}))
        await asyncio.sleep(0.1)
        return self._state.copy()

    async def set_state(self, state: dict) -> bool:
        await self._ws.send(json.dumps({"type": "set_state", "id": self.device_id, "state": state}))
        return True

    async def _listen(self):
        async for msg in self._ws:
            try:
                data = json.loads(msg)
                if data.get("id") == self.device_id:
                    self._state.update(data.get("state", {}))
            except Exception:
                pass
```
