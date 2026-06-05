"""
Script học IR code từ Broadlink RM mini.
Chạy: python3 learn_ir.py
"""
import broadlink, time, base64, json, os

print("Đang tìm Broadlink...")
devices = broadlink.discover(timeout=5)
if not devices:
    print("Không tìm thấy thiết bị Broadlink!")
    exit(1)

rm = devices[0]
rm.auth()
print(f"Kết nối: {rm.model} @ {rm.host[0]}\n")

codes = {}
buttons = [
    ("on",       "BẬT"),
    ("off",      "TẮT"),
    ("temp_18",  "18°C"),
    ("temp_20",  "20°C"),
    ("temp_22",  "22°C"),
    ("temp_24",  "24°C"),
    ("temp_25",  "25°C"),
    ("temp_26",  "26°C"),
    ("mode_cool","Mode COOL"),
    ("mode_fan", "Mode FAN"),
    ("fan_auto", "Fan AUTO"),
    ("fan_low",  "Fan LOW"),
    ("fan_high", "Fan HIGH"),
]

for key, label in buttons:
    while True:
        input(f"[{label}] Cầm remote, nhấn Enter rồi bấm nút ngay... ")
        print(f"  Đang học... (nhấn nút {label} ngay!)")
        rm.enter_learning()
        time.sleep(5)
        try:
            code = rm.check_data()
            b64 = base64.b64encode(code).decode()
            codes[key] = b64
            print(f"  ✓ OK — {b64[:40]}...")
            break
        except Exception as e:
            print(f"  ✗ Không nhận được ({e}). Thử lại.")

    skip = input("  Học nút tiếp theo? (Enter=có, s=bỏ qua còn lại) ")
    if skip.lower() == 's':
        break

# Lưu ra file
out = "ir_codes.json"
with open(out, "w") as f:
    json.dump({"ir.ac_living_room": codes}, f, indent=2)
print(f"\nĐã lưu vào {out}")
print("Copy nội dung vào devices.yaml → config của ir.ac_living_room")
