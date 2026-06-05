# References Index

Purpose: catalog documentation/reference material for the `references/` layer of 4home.

Updated: 2026-06-05

## Contract

`references/` contains reusable notes, templates, protocol/device documentation, and design references.

Do not place runtime source code, secrets, or app config here; use `../source/` for runtime material.

## Folder Guide

Hiện tại `references/` là một layer phẳng, chưa tách subfolder. Khi tài liệu nhiều lên, có thể tách theo nhóm sau:

- `architecture/` — thiết kế hệ thống, controller/core/driver boundaries, event/rule flow.
- `devices/` — inventory thiết bị, model, protocol, IP/MAC/local-key status không chứa secret.
- `protocols/` — note kỹ thuật cho MQTT, Tuya, BLE, ESPHome, Broadlink, Frigate, Miio.
- `templates/` — template driver/config/automation dùng lại.
- `decisions/` — quyết định thiết kế và trade-off đã chốt.

Quy tắc: reference files phải giúp người/agent hiểu hoặc thiết kế hệ thống, nhưng không được là source runtime bắt buộc để app chạy.

## Contents

- `driver_templates.md` — reusable driver templates and protocol examples.
- `index.md` — this catalog.
- `log.md` — append-only operational timeline for reference-layer changes.

## Suggested future reference pages

- `architecture.md` — high-level controller/core/driver architecture.
- `device-inventory.md` — physical device inventory, model, protocol, IP/MAC/local-key status without secrets.
- `protocol-notes.md` — MQTT/Tuya/BLE/ESPHome/Broadlink/Frigate notes.
- `automation-design.md` — automation rule examples and decision history.
