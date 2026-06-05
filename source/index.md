# Source Index

Purpose: catalog runtime/source files for the `source/` layer of 4home.

Updated: 2026-06-05

## Contract

`source/` contains all runtime project material: Python source code, device config, ESPHome templates, dependency files, and local environment examples.

Do not place reference-only documentation here; use `../references/` for that.

## Folder Guide

- `core/` — lõi framework: interface driver, registry, rule engine, event bus. Code trong đây điều phối driver qua interface chung và không phụ thuộc giao thức thiết bị cụ thể.
- `drivers/` — adapter/driver theo giao thức hoặc nền tảng thiết bị. Mỗi driver map raw API/protocol response sang state schema chung và map state command ngược về protocol gốc.
- `config/` — cấu hình runtime: device registry và automation rules. Được phép dùng `${VAR}` để tham chiếu env; không hardcode secret.
- `esphome_configs/` — template/cấu hình ESPHome/ESP32 để tạo node thiết bị thực.

Files trực tiếp trong `source/`:

- `index.md` — catalog cho source layer.
- `log.md` — append-only timeline cho source layer.
- `requirements.txt` — Python dependencies.
- `.env.example` — env template safe to commit.
- `.env` — local secrets/config only; không commit.
- `cli.py` — entrypoint CLI khi được thêm.

## Contents

### Core

- `core/base_driver.py` — base async interface every driver implements.
- `core/device_registry.py` — loads `config/devices.yaml`, expands env vars, instantiates drivers.
- `core/__init__.py` — package marker.

### Drivers

- `drivers/broadlink_driver.py` — Broadlink IR control driver.
- `drivers/esphome_driver.py` — ESPHome API driver.
- `drivers/frigate_driver.py` — Frigate camera driver.
- `drivers/miio_driver.py` — Xiaomi Miio driver.
- `drivers/pc_driver.py` — PC power/status driver via WoL/SSH/ping.
- `drivers/tuya_driver.py` — Tuya local driver.
- `drivers/xiaomi_ble_driver.py` — Xiaomi BLE sensor driver.
- `drivers/__init__.py` — package marker.

### Configuration

- `config/devices.yaml` — current device registry config; 17 devices as of this index.
- `.env.example` — environment variable template safe to commit.
- `.env` — local secrets/config only; do not commit.

### Runtime templates and dependencies

- `esphome_configs/esp32_template.yaml` — ESP32/ESPHome template.
- `requirements.txt` — Python dependencies.

## Missing but planned by instruction

- `core/automation.py` — rule engine.
- `core/event_bus.py` — observer/event bus for state changes.
- `config/automations.yaml` — automation rules.
- `cli.py` — command-line entrypoint.
- Protocol placeholders from the original instruction: `mqtt_driver.py`, `http_driver.py`, `ws_driver.py`, `ir_driver.py`, `shell_driver.py`.
