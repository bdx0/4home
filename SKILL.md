---
name: 4home
description: |
  Xây dựng và điều khiển hệ thống home automation tự viết driver. Dùng ngay khi người dùng đề cập đến:
  - Điều khiển thiết bị: "bật đèn", "tắt điều hòa", "đóng rèm", "kiểm tra trạng thái"
  - Viết driver thiết bị: đèn, AC, rèm, ổ cắm, cảm biến, camera, khóa cửa
  - Giao thức IoT: MQTT, HTTP/REST, WebSocket, Tuya, Zigbee, Z-Wave, IR, BLE, Modbus
  - Tự xây dựng hệ thống smart home: kiến trúc, device registry, automation rules
  - Debug kết nối thiết bị, state sync, protocol sniffing
  - Các từ khóa: "4home", "smart home", "IoT driver", "home automation", "điều khiển thiết bị nhà"

  Trigger ngay cả khi người dùng chỉ nói tên thiết bị ("đèn phòng khách", "điều hòa") kèm hành động.
---

# 4home — Hệ Thống Home Automation Tự Xây

Skill này giúp thiết kế, viết code, và điều khiển hệ thống smart home hoàn toàn tự làm — không phụ thuộc nền tảng thương mại.

## Triết lý thiết kế

**Mỗi thiết bị = một driver, mọi driver đều nói cùng một ngôn ngữ.** Phần core không cần biết thiết bị dùng MQTT hay HTTP hay Zigbee — chỉ gọi `get_state()` và `set_state()`. Thêm thiết bị mới mà không đụng code core.

## Kiến trúc thư mục

```
4home/
├── core/
│   ├── base_driver.py        # Interface bắt buộc cho mọi driver
│   ├── device_registry.py    # Load config, quản lý thiết bị
│   ├── automation.py         # Rule engine
│   └── event_bus.py          # Observer pattern cho state changes
├── drivers/
│   ├── mqtt_driver.py
│   ├── http_driver.py
│   ├── ws_driver.py
│   ├── tuya_driver.py
│   ├── ir_driver.py
│   └── shell_driver.py
├── config/
│   ├── devices.yaml
│   └── automations.yaml
├── .env
└── cli.py
```

## BaseDriver Interface

Mọi driver PHẢI implement đúng interface này:

```python
from abc import ABC, abstractmethod
from typing import Callable, Awaitable

class BaseDriver(ABC):
    def __init__(self, device_id: str, config: dict):
        self.device_id = device_id
        self.config = config

    @abstractmethod
    async def connect(self) -> bool:
        """Kết nối tới thiết bị/broker. Trả về True nếu thành công."""

    @abstractmethod
    async def disconnect(self):
        """Ngắt kết nối sạch sẽ."""

    @abstractmethod
    async def get_state(self) -> dict:
        """Lấy trạng thái hiện tại. Trả về dict theo schema của device type."""

    @abstractmethod
    async def set_state(self, state: dict) -> bool:
        """Áp dụng state mới. Chỉ truyền các field cần thay đổi."""

    async def on_state_change(self, callback: Callable[[dict], Awaitable[None]]):
        """Đăng ký callback khi thiết bị tự báo state thay đổi (push-based)."""
        pass  # Optional — chỉ implement nếu thiết bị hỗ trợ push
```

## State Schemas theo Device Type

| Type | Fields |
|------|--------|
| `light` | `on: bool, brightness: int (0-100), color_temp: int (kelvin), rgb: [r,g,b]` |
| `ac` | `on: bool, temp: float, mode: "cool"\|"heat"\|"fan"\|"dry"\|"auto", fan: "auto"\|"low"\|"mid"\|"high"` |
| `curtain` | `position: int (0=đóng, 100=mở), moving: bool` |
| `plug` | `on: bool, power_w: float, energy_kwh: float` |
| `sensor` | `temperature: float, humidity: float, motion: bool, door_open: bool, lux: float` |
| `camera` | `streaming: bool, recording: bool, rtsp_url: str` |
| `lock` | `locked: bool, battery_pct: int` |
| `fan` | `on: bool, speed: int (0-100), oscillating: bool` |
| `tv` | `on: bool, volume: int, channel: int, input: str` |

Driver chỉ trả về những field mà thiết bị thực sự hỗ trợ.

## Config mẫu (devices.yaml)

```yaml
devices:
  - id: light.living_room
    name: Đèn phòng khách
    type: light
    driver: mqtt
    config:
      broker: "mqtt://192.168.1.10"
      topic_state: "home/lights/living_room/state"
      topic_set: "home/lights/living_room/set"

  - id: ac.bedroom
    name: Điều hòa phòng ngủ
    type: ac
    driver: http
    config:
      base_url: "http://192.168.1.101"
      auth: {type: bearer, token: "${AC_TOKEN}"}

  - id: curtain.bedroom
    name: Rèm phòng ngủ
    type: curtain
    driver: tuya
    config:
      device_id: "abc123xyz"
      local_key: "${CURTAIN_KEY}"
      ip: "192.168.1.102"
```

## Automation Rules (automations.yaml)

```yaml
automations:
  - name: "Về nhà buổi tối"
    trigger:
      type: time
      at: "18:30"
    actions:
      - device: light.living_room
        state: {on: true, brightness: 70}
      - device: ac.bedroom
        state: {on: true, temp: 26, mode: cool}

  - name: "Tắt khi ra ngoài"
    trigger:
      type: device_state
      device: sensor.door
      condition: {door_open: true}
    conditions:
      - {type: time, after: "07:00", before: "22:00"}
    actions:
      - device: "light.*"
        state: {on: false}
      - device: "ac.*"
        state: {on: false}
```

## Workflow khi viết driver mới

Hỏi người dùng:
1. Thiết bị model gì? Có API doc không?
2. Giao thức: MQTT, HTTP, Tuya local, IR, Zigbee...?
3. Authentication: local key, token, hay không cần?

Sau đó:
1. Tạo `drivers/<protocol>_driver.py` implement `BaseDriver`
2. Viết `_parse_state()` — map raw API response → state schema
3. Viết `_build_command()` — map state dict → raw API command
4. Thêm retry với exponential backoff cho `connect()`
5. Thêm vào `devices.yaml`

Xem `references/driver_templates.md` để có template sẵn cho từng giao thức.

## Workflow khi điều khiển bằng ngôn ngữ tự nhiên

| Lệnh tự nhiên | Device ID | State |
|--------------|-----------|-------|
| "bật đèn phòng khách" | `light.living_room` | `{on: true}` |
| "tắt điều hòa" | `ac.*` | `{on: false}` |
| "đèn 50%" | light đang được nhắc | `{brightness: 50}` |
| "điều hòa 25 độ" | `ac.*` | `{temp: 25}` |
| "đóng rèm phòng ngủ" | `curtain.bedroom` | `{position: 0}` |
| "tắt tất cả đèn" | `light.*` | `{on: false}` |

## Debugging

```bash
# Test MQTT
mosquitto_sub -h 192.168.1.10 -t "home/#" -v

# Test HTTP
curl -v http://192.168.1.101/api/status

# Tuya local
python -c "import tinytuya; d = tinytuya.Device('id','ip','key'); print(d.status())"

# Protocol sniffing
mitmproxy  # capture traffic từ app gốc của thiết bị
```

## Dependencies

```bash
# Python
pip install asyncio aiohttp paho-mqtt tinytuya python-dotenv pyyaml broadlink

# TypeScript
npm install mqtt axios ws dotenv
```
