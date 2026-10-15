"""
Generate synthetic cabinet panel images with readable labels for testing.
Each image has a mix of:
  - Clear labels that match the Excel list -> PASS
  - Missing labels -> FAIL
  - Degraded/small labels -> UNREADABLE
  - Colored wires for color checks
"""
import cv2
import numpy as np
from pathlib import Path
from openpyxl import Workbook

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "test-inputs"
OUT.mkdir(parents=True, exist_ok=True)

SETS = [
    {
        "id": "set1",
        "name": "Power Distribution Panel",
        "present_labels": ["PS11", "CB41", "CB42", "X3", "PE"],
        "missing_labels": ["PS12", "D12"],
        "degraded_labels": ["KS2"],
        "wires": [("red", "24V+"), ("blue", "N"), ("green", "PE"), ("black", "0V")],
        "ferrules": ["X3-1", "X3-2"],
    },
    {
        "id": "set2",
        "name": "Motor Control Cabinet",
        "present_labels": ["VFD01", "CB10", "K1", "PLC1"],
        "missing_labels": ["BRAKE", "FAN-M"],
        "degraded_labels": ["TS1", "F5"],
        "wires": [("red", "L1"), ("blue", "N"), ("yellow", "E"), ("black", "L2"), ("orange", "CTRL")],
        "ferrules": ["M1-U", "M1-V"],
    },
    {
        "id": "set3",
        "name": "Automation Panel",
        "present_labels": ["PLC02", "HMI01", "SW24V", "ETH-SW"],
        "missing_labels": ["IO-M1", "TEMP-S"],
        "degraded_labels": ["AO1"],
        "wires": [("red", "24V"), ("blue", "0V"), ("white", "SIG"), ("green", "PE")],
        "ferrules": ["AI-1", "AI-2"],
    },
    {
        "id": "set4",
        "name": "Lighting Control Panel",
        "present_labels": ["MCB1", "MCB2", "MCB3", "RCD1", "DALI"],
        "missing_labels": ["MCB4"],
        "degraded_labels": ["PIR1", "LUX1"],
        "wires": [("brown", "L"), ("blue", "N"), ("green", "PE"), ("grey", "SW")],
        "ferrules": ["L1-OUT", "L2-OUT"],
    },
    {
        "id": "set5",
        "name": "HVAC Control Cabinet",
        "present_labels": ["AHU-C", "VSD1", "CT1", "FILTER"],
        "missing_labels": ["DAMPER", "VALVE"],
        "degraded_labels": ["PT100"],
        "wires": [("red", "24V"), ("blue", "0V"), ("orange", "AI"), ("white", "AO"), ("black", "COM")],
        "ferrules": ["T1-IN", "T2-IN"],
    },
]

WIRE_COLORS = {
    "red": (0, 0, 220), "blue": (200, 100, 0), "green": (0, 180, 0),
    "yellow": (0, 220, 220), "black": (30, 30, 30), "white": (240, 240, 240),
    "brown": (30, 70, 140), "orange": (0, 140, 240), "grey": (160, 160, 160),
}


def draw_cabinet(s):
    W, H = 1200, 900
    img = np.full((H, W, 3), (230, 230, 230), dtype=np.uint8)

    cv2.rectangle(img, (40, 40), (W - 40, H - 40), (60, 60, 60), 3)
    cv2.rectangle(img, (50, 50), (W - 50, H - 50), (200, 200, 200), -1)
    cv2.rectangle(img, (50, 50), (W - 50, H - 50), (100, 100, 100), 2)

    cv2.putText(img, s["name"].upper(), (70, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)

    cv2.line(img, (60, 105), (W - 60, 105), (150, 150, 150), 1)

    y_pos = 140
    x_pos = 80

    for label in s["present_labels"]:
        bw, bh = 140, 80
        if x_pos + bw > W - 80:
            x_pos = 80
            y_pos += bh + 30

        color = (180 + np.random.randint(-20, 20), 180 + np.random.randint(-20, 20), 190)
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + bw, y_pos + bh), color, -1)
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + bw, y_pos + bh), (80, 80, 80), 2)

        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        tx = x_pos + (bw - text_size[0]) // 2
        ty = y_pos + (bh + text_size[1]) // 2
        cv2.putText(img, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (10, 10, 10), 2)

        status_color = (0, 180, 0)
        cv2.circle(img, (x_pos + bw - 12, y_pos + 12), 5, status_color, -1)

        x_pos += bw + 25

    for label in s["degraded_labels"]:
        bw, bh = 110, 60
        if x_pos + bw > W - 80:
            x_pos = 80
            y_pos += 110

        color = (175, 175, 180)
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + bw, y_pos + bh), color, -1)
        cv2.rectangle(img, (x_pos, y_pos), (x_pos + bw, y_pos + bh), (150, 150, 150), 1)

        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        tx = x_pos + (bw - text_size[0]) // 2
        ty = y_pos + (bh + text_size[1]) // 2
        cv2.putText(img, label, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (155, 155, 158), 1)

        roi = img[y_pos:y_pos + bh, x_pos:x_pos + bw].copy()
        roi = cv2.GaussianBlur(roi, (7, 7), 2.0)
        noise = np.random.randint(0, 25, (bh, bw, 3), dtype=np.uint8)
        roi = cv2.add(roi, noise)
        img[y_pos:y_pos + bh, x_pos:x_pos + bw] = roi

        x_pos += bw + 25

    y_pos += 130
    cv2.line(img, (60, y_pos - 15), (W - 60, y_pos - 15), (150, 150, 150), 1)
    cv2.putText(img, "TERMINAL BLOCK", (70, y_pos + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    y_pos += 15

    tb_x = 80
    for ferrule in s.get("ferrules", []):
        tw, th = 50, 30
        cv2.rectangle(img, (tb_x, y_pos), (tb_x + tw, y_pos + th), (160, 160, 160), -1)
        cv2.rectangle(img, (tb_x, y_pos), (tb_x + tw, y_pos + th), (80, 80, 80), 1)
        fsize = cv2.getTextSize(ferrule, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
        cv2.putText(img, ferrule, (tb_x + (tw - fsize[0]) // 2, y_pos + th - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (30, 30, 30), 1)
        tb_x += tw + 10

    wire_y = y_pos + 60
    cv2.putText(img, "WIRING", (70, wire_y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    wx = 80
    wire_w = 30
    wire_gap = 50
    for color_name, wire_label in s["wires"]:
        bgr = WIRE_COLORS.get(color_name, (128, 128, 128))
        cv2.rectangle(img, (wx, wire_y + 5), (wx + wire_w, wire_y + 100), bgr, -1)
        cv2.rectangle(img, (wx, wire_y + 5), (wx + wire_w, wire_y + 100), (60, 60, 60), 1)
        cv2.putText(img, wire_label, (wx, wire_y + 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (80, 80, 80), 1)
        wx += wire_w + wire_gap

    din_y = H - 100
    cv2.rectangle(img, (60, din_y), (W - 60, din_y + 8), (140, 160, 140), -1)
    cv2.rectangle(img, (60, din_y + 25), (W - 60, din_y + 33), (140, 160, 140), -1)
    cv2.putText(img, "DIN RAIL", (70, din_y + 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)

    return img


def create_label_excel(path, s):
    wb = Workbook()
    ws = wb.active
    ws.title = "Labels"
    ws.append(["Device", "Expected Label", "Position"])
    for label in s["present_labels"]:
        ws.append([f"Component {label}", label, "Panel"])
    for label in s["missing_labels"]:
        ws.append([f"Component {label}", label, "Panel"])
    for label in s["degraded_labels"]:
        ws.append([f"Component {label}", label, "Panel"])
    wb.save(str(path))


def create_wire_excel(path, s):
    wb = Workbook()
    ws = wb.active
    ws.title = "Wires"
    ws.append(["Wire ID", "From", "To", "Color", "Ferrule ID"])
    for i, (color, wire_label) in enumerate(s["wires"]):
        ferrule = s["ferrules"][i] if i < len(s.get("ferrules", [])) else ""
        ws.append([f"W{i + 1:03d}", f"SRC-{wire_label}", f"DST-{wire_label}", color.capitalize(), ferrule])
    wb.save(str(path))


def create_ga_pdf(path, s):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.colors import HexColor

    c = pdfcanvas.Canvas(str(path), pagesize=landscape(A4))
    w, h = landscape(A4)
    c.setFillColor(HexColor("#F5F5F5"))
    c.rect(0, 0, w, h, fill=1)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(HexColor("#1a1a1a"))
    c.drawString(20 * mm, h - 20 * mm, f"GA - {s['name'].upper()}")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#666"))
    c.drawString(20 * mm, h - 28 * mm, "CabinetSight Test Reference | Rev A")

    panel_x, panel_y = 25 * mm, 25 * mm
    panel_w, panel_h = w - 50 * mm, h - 55 * mm
    c.setStrokeColor(HexColor("#333"))
    c.setLineWidth(2)
    c.setFillColor(HexColor("#E8E8E8"))
    c.rect(panel_x, panel_y, panel_w, panel_h, fill=1, stroke=1)

    all_labels = s["present_labels"] + s["missing_labels"] + s["degraded_labels"]
    colors = ["#4A90D9", "#5CB85C", "#D9534F", "#F0AD4E", "#337AB7", "#9B59B6", "#1ABC9C", "#E67E22"]
    cols = 4
    margin = 10 * mm
    gap = 8 * mm
    box_w = (panel_w - 2 * margin - (cols - 1) * gap) / cols
    box_h = 28 * mm

    for i, label in enumerate(all_labels):
        row = i // cols
        col = i % cols
        x = panel_x + margin + col * (box_w + gap)
        y = panel_y + panel_h - margin - (row + 1) * (box_h + gap)
        c.setFillColor(HexColor(colors[i % len(colors)]))
        c.rect(x, y, box_w, box_h, fill=1, stroke=1)
        c.setFillColor(HexColor("#FFF"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(x + box_w / 2, y + box_h / 2 - 3, label)

    c.save()


def main():
    print("=" * 55)
    print("  Generating 5 Cabinet Test Sets with OCR-readable text")
    print("=" * 55)

    for s in SETS:
        sid = s["id"]
        d = OUT / sid
        d.mkdir(exist_ok=True)

        img = draw_cabinet(s)
        photo_path = d / f"{sid}_photo.jpg"
        cv2.imwrite(str(photo_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"\n{sid}: {s['name']}")
        print(f"  Photo:  {photo_path.name} ({img.shape[1]}x{img.shape[0]})")
        print(f"  PASS labels:       {s['present_labels']}")
        print(f"  FAIL labels:       {s['missing_labels']}")
        print(f"  UNREADABLE labels: {s['degraded_labels']}")

        label_path = d / f"{sid}_label_list.xlsx"
        create_label_excel(label_path, s)
        print(f"  Labels: {label_path.name}")

        wire_path = d / f"{sid}_wire_list.xlsx"
        create_wire_excel(wire_path, s)
        print(f"  Wires:  {wire_path.name}")

        ga_path = d / f"{sid}_ga_drawing.pdf"
        create_ga_pdf(ga_path, s)
        print(f"  GA PDF: {ga_path.name}")

    print(f"\n{'=' * 55}")
    print(f"Done! Files in: {OUT}")
    print(f"Each set has clear + missing + degraded labels")
    print(f"for a genuine mix of PASS / FAIL / UNREADABLE.")


if __name__ == "__main__":
    main()
