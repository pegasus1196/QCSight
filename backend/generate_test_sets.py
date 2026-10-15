"""
Generate 5 complete test input sets for CabinetSight.
Each set: photo (from dataset) + GA drawing PDF + wire list + label list.
Crafted to produce a realistic mix of PASS / FAIL / UNREADABLE / CLOSED.
"""
import shutil
from pathlib import Path
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).parent.parent
DATASET = ROOT / "backend" / "training" / "dataset" / "circuit-elements" / "train" / "images"
OUT = ROOT / "assets" / "test-inputs"
OUT.mkdir(parents=True, exist_ok=True)

TEST_SETS = [
    {
        "id": "set1",
        "name": "Raspberry Pi Control Board",
        "src_prefix": "RPI3B_Top",
        "devices": [
            ("USB Port", "USB-A1", "Top-right"),
            ("Ethernet Jack", "ETH-01", "Top-right"),
            ("GPIO Header", "GPIO-40P", "Right-side"),
            ("HDMI Port", "HDMI-01", "Bottom-left"),
            ("Power IC", "LM2596", "Center"),
            ("SD Card Slot", "SD-01", "Bottom"),
            ("LED Indicator", "LED-PWR", "Top-left"),
        ],
        "wires": [
            ("W01", "5V", "GPIO:Pin2", "Red", "5V-P2"),
            ("W02", "GND", "GPIO:Pin6", "Black", "GND-P6"),
            ("W03", "3.3V", "GPIO:Pin1", "Orange", "3V3-P1"),
            ("W04", "TX", "GPIO:Pin8", "Green", "TX-P8"),
            ("W05", "RX", "GPIO:Pin10", "Yellow", "RX-P10"),
            ("W06", "SDA", "GPIO:Pin3", "Blue", "SDA-P3"),
        ],
        "colors": [("5V Rail", "red"), ("Ground", "black"), ("Signal", "green")],
    },
    {
        "id": "set2",
        "name": "Industrial ML Board",
        "src_prefix": "ML365_Top",
        "devices": [
            ("Main Processor", "CPU-01", "Center"),
            ("RAM Module", "DDR3-U1", "Center-right"),
            ("Flash Memory", "NAND-01", "Top-center"),
            ("Power Regulator", "VR-5V", "Bottom-left"),
            ("Ethernet PHY", "PHY-01", "Top-right"),
            ("Debug Header", "JTAG-01", "Left"),
            ("Crystal Oscillator", "Y1-25MHz", "Center"),
            ("DC Input Jack", "J1-12V", "Bottom-right"),
        ],
        "wires": [
            ("W01", "12V-IN", "VR-5V:IN", "Red", "J1-VIN"),
            ("W02", "5V-OUT", "CPU:VCC", "Orange", "VR-5V"),
            ("W03", "GND", "GND-Plane", "Black", "GND"),
            ("W04", "ETH-TX+", "PHY:TX+", "Green", "ETH-1"),
            ("W05", "ETH-TX-", "PHY:TX-", "White", "ETH-2"),
            ("W06", "JTAG-TDI", "CPU:TDI", "Blue", "JTAG-1"),
        ],
        "colors": [("Power", "red"), ("Ground", "black"), ("Data", "blue"), ("Signal", "green")],
    },
    {
        "id": "set3",
        "name": "FPGA Development Board",
        "src_prefix": "MicroZed_Top",
        "devices": [
            ("FPGA Chip", "XC7Z010", "Center"),
            ("DDR Memory", "DDR3-256M", "Center-left"),
            ("USB-UART", "FT2232H", "Top-right"),
            ("Power Module", "PWR-3V3", "Bottom-left"),
            ("Config Flash", "QSPI-01", "Left"),
            ("Clock Generator", "CLK-100M", "Center"),
            ("Expansion Header", "JA-PMOD", "Right"),
            ("Status LED", "LED-DONE", "Top"),
        ],
        "wires": [
            ("W01", "3.3V", "FPGA:VCCIO", "Red", "3V3-IO"),
            ("W02", "1.0V", "FPGA:VCCINT", "Orange", "1V-INT"),
            ("W03", "GND", "GND-PAD", "Black", "GND-0"),
            ("W04", "CLK", "FPGA:CLK0", "Blue", "CLK-100"),
            ("W05", "UART-TX", "FT2232:RXD", "Green", "UART-TX"),
            ("W06", "JTAG-TCK", "FPGA:TCK", "White", "JTAG-T"),
        ],
        "colors": [("VCCIO", "red"), ("Ground", "black"), ("Clock", "blue")],
    },
    {
        "id": "set4",
        "name": "Motor Controller Panel",
        "src_prefix": "DuetWIFI_Top",
        "devices": [
            ("Stepper Driver", "TMC2660-X", "Center-left"),
            ("Stepper Driver", "TMC2660-Y", "Center"),
            ("Stepper Driver", "TMC2660-Z", "Center-right"),
            ("Main MCU", "SAM4E8E", "Top-center"),
            ("WiFi Module", "ESP8266", "Top-right"),
            ("Power MOSFET", "Q1-BED", "Bottom-left"),
            ("Fuse Holder", "F1-15A", "Bottom-right"),
            ("Thermistor Input", "TH-BED", "Bottom"),
        ],
        "wires": [
            ("W01", "24V-IN", "VIN-TERM", "Red", "VIN-24"),
            ("W02", "MOTOR-X", "TMC-X:OUT", "Blue", "MOT-X"),
            ("W03", "MOTOR-Y", "TMC-Y:OUT", "Green", "MOT-Y"),
            ("W04", "MOTOR-Z", "TMC-Z:OUT", "Yellow", "MOT-Z"),
            ("W05", "BED-HTR", "Q1:DRAIN", "Red", "BED-H"),
            ("W06", "GND-POWER", "GND-BUS", "Black", "GND-P"),
        ],
        "colors": [("24V Power", "red"), ("Ground", "black"), ("Motor A", "blue"), ("Motor B", "green")],
    },
    {
        "id": "set5",
        "name": "Embedded System PCB",
        "src_prefix": "pcb163rec1",
        "devices": [
            ("Microcontroller", "STM32F4", "Center"),
            ("CAN Transceiver", "MCP2551", "Top-right"),
            ("Buck Converter", "LM2576", "Bottom-left"),
            ("USB Connector", "USB-B", "Left"),
            ("Programming Header", "SWD-6P", "Top"),
            ("Crystal", "Y1-8MHz", "Center"),
            ("Capacitor Bank", "C1-C10", "Bottom"),
        ],
        "wires": [
            ("W01", "5V-USB", "LM2576:IN", "Red", "USB-5V"),
            ("W02", "3.3V", "STM32:VDD", "Orange", "3V3"),
            ("W03", "CAN-H", "MCP2551:CANH", "Blue", "CAN-H"),
            ("W04", "CAN-L", "MCP2551:CANL", "White", "CAN-L"),
            ("W05", "SWDIO", "STM32:SWDIO", "Green", "SWD-IO"),
            ("W06", "GND", "GND-PLANE", "Black", "GND"),
        ],
        "colors": [("Power", "red"), ("CAN-H", "blue"), ("Ground", "black")],
    },
]


def find_image(prefix):
    for img in sorted(DATASET.glob("*.jpg")):
        if img.name.startswith(prefix):
            return img
    return None


def create_excel(path, title, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append(headers)
    for row in rows:
        ws.append(list(row))
    wb.save(str(path))


def create_ga_pdf(path, name, devices):
    c = canvas.Canvas(str(path), pagesize=landscape(A4))
    w, h = landscape(A4)

    c.setFillColor(HexColor("#F5F5F5"))
    c.rect(0, 0, w, h, fill=1)

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(HexColor("#1a1a1a"))
    c.drawString(20 * mm, h - 20 * mm, f"GA DRAWING — {name.upper()}")

    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#666"))
    c.drawString(20 * mm, h - 28 * mm, f"CabinetSight Test Reference  |  Rev A  |  2026-10-12")

    panel_x, panel_y = 25 * mm, 25 * mm
    panel_w, panel_h = w - 50 * mm, h - 55 * mm
    c.setStrokeColor(HexColor("#333"))
    c.setLineWidth(2)
    c.setFillColor(HexColor("#E8E8E8"))
    c.rect(panel_x, panel_y, panel_w, panel_h, fill=1, stroke=1)

    colors = ["#4A90D9", "#5CB85C", "#D9534F", "#F0AD4E", "#337AB7", "#9B59B6", "#1ABC9C", "#E67E22"]
    cols = 4
    margin = 10 * mm
    gap = 8 * mm
    box_w = (panel_w - 2 * margin - (cols - 1) * gap) / cols
    box_h = 28 * mm

    for i, (dev_name, dev_id, position) in enumerate(devices):
        row = i // cols
        col = i % cols
        x = panel_x + margin + col * (box_w + gap)
        y = panel_y + panel_h - margin - (row + 1) * (box_h + gap)

        color = colors[i % len(colors)]
        c.setFillColor(HexColor(color))
        c.setStrokeColor(HexColor("#333"))
        c.setLineWidth(1)
        c.rect(x, y, box_w, box_h, fill=1, stroke=1)

        c.setFillColor(HexColor("#FFF"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + box_w / 2, y + box_h - 12, dev_id)
        c.setFont("Helvetica", 7)
        c.drawCentredString(x + box_w / 2, y + box_h - 22, dev_name)
        c.setFont("Helvetica", 6)
        c.setFillColor(HexColor("#DDD"))
        c.drawCentredString(x + box_w / 2, y + 4, position)

    c.setStrokeColor(HexColor("#333"))
    c.setLineWidth(1)
    c.rect(20 * mm, 8 * mm, w - 40 * mm, 14 * mm, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(HexColor("#1a1a1a"))
    c.drawString(25 * mm, 16 * mm, f"{name}  |  CabinetSight Test  |  Project Eagle Eye")
    c.setFont("Helvetica", 7)
    c.drawString(25 * mm, 10 * mm, "Emerson Problem Statement #03  |  Sheet 1/1")

    c.save()


def main():
    print("=" * 55)
    print("  CabinetSight — Generating 5 Test Input Sets")
    print("=" * 55)

    for s in TEST_SETS:
        sid = s["id"]
        name = s["name"]
        print(f"\n--- {sid}: {name} ---")

        set_dir = OUT / sid
        set_dir.mkdir(exist_ok=True)

        src_img = find_image(s["src_prefix"])
        if src_img:
            dst = set_dir / f"{sid}_photo.jpg"
            shutil.copy2(src_img, dst)
            print(f"  Photo:   {dst.name}")
        else:
            print(f"  Photo:   NOT FOUND (prefix: {s['src_prefix']})")

        ga_path = set_dir / f"{sid}_ga_drawing.pdf"
        create_ga_pdf(ga_path, name, s["devices"])
        print(f"  Drawing: {ga_path.name}")

        label_path = set_dir / f"{sid}_label_list.xlsx"
        create_excel(
            label_path, "Labels",
            ["Device", "Expected Label", "Position"],
            [(d[0], d[1], d[2]) for d in s["devices"]],
        )
        print(f"  Labels:  {label_path.name} ({len(s['devices'])} devices)")

        wire_path = set_dir / f"{sid}_wire_list.xlsx"
        create_excel(
            wire_path, "Wires",
            ["Wire ID", "From", "To", "Color", "Ferrule ID"],
            s["wires"],
        )
        print(f"  Wires:   {wire_path.name} ({len(s['wires'])} wires)")

    demo_photo = ROOT / "assets" / "cabinet-demo.png"
    demo_dir = OUT / "set0_demo"
    demo_dir.mkdir(exist_ok=True)
    if demo_photo.exists():
        shutil.copy2(demo_photo, demo_dir / "set0_photo.png")

    print(f"\n{'=' * 55}")
    print(f"  All sets ready in: {OUT}")
    print(f"  Open in Explorer: assets\\test-inputs\\")
    print(f"{'=' * 55}")
    print(f"\nHow to use:")
    print(f"  1. Open http://127.0.0.1:8000")
    print(f"  2. Scroll to Workspace")
    print(f"  3. Browse to assets/test-inputs/set1/ (or set2-5)")
    print(f"  4. Upload: photo > drawing > wire list > label list")
    print(f"  5. Hit 'Run Inspection'")


if __name__ == "__main__":
    main()
