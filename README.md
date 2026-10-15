# CabinetSight — Project EAGLE EYE

**AI-Powered Electrical Cabinet Quality Control Inspector**

> VIT Code Apex 3.0 | Emerson Problem Statement #03

---

## Overview

CabinetSight automates visual quality inspection of electrical cabinets by comparing a photograph of the built cabinet against its engineering drawings and specification files. It replaces manual checklist-based QC with a computer vision pipeline that runs **entirely on-device** — no cloud, no telemetry.

## Key Features

| Module | Method | What It Does |
|--------|--------|-------------|
| Device Presence | ORB + SIFT | Verifies every component from the GA drawing exists in the cabinet |
| Label Verification | EasyOCR + RapidFuzz | OCR reads labels and fuzzy-matches against expected list (80% threshold) |
| Wire Ferrules | ROI + OCR | Detects ferrule markings on wire ends and validates against wire list |
| Photo Alignment | Homography + RANSAC | Registers cabinet photo to GA drawing with SSIM scoring |
| Wire Colour | HSV Masking + K-Means | Validates wire colours against IEC 60446 standard |
| YOLO Detection | YOLOv11 | Object detection across 45 electrical component classes |

### Closed-Loop Inspection

Every **FAIL** generates a step-by-step AI corrective suggestion — which tool to use, where to fix, how to verify. After the operator fixes the issue and re-photographs, a **re-check** run automatically marks resolved items as **CLOSED**.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, Uvicorn |
| Computer Vision | OpenCV 5.0 (ORB, SIFT, homography, HSV, contours) |
| OCR | EasyOCR (CRAFT + CRNN), Tesseract fallback |
| Fuzzy Matching | RapidFuzz (token_sort_ratio) |
| Object Detection | Ultralytics YOLOv11 |
| Data Parsing | openpyxl (.xlsx), ReportLab (PDF generation) |
| Frontend | Vanilla HTML/CSS/JS (no framework dependencies) |

## System Architecture

```
INPUT               PROCESSING          AI MODELS            OUTPUT
─────               ──────────          ─────────            ──────
Cabinet Photo  ──►  FastAPI Server ──►  ORB + SIFT      ──►  QC Checklist
GA Drawing     ──►  CV Inspector   ──►  CRAFT + CRNN    ──►  AI Suggestions
Wire List      ──►  OCR Reader     ──►  YOLOv11         ──►  PDF / CSV Report
Label List     ──►  Color Analyzer ──►  K-Means + HSV   ──►  Re-Check Loop
                                                    ▲              │
                                                    └──── CLOSED ◄─┘
```

## YOLO Model & Dataset

**Dataset:** [LibreYOLO/circuit-elements](https://huggingface.co/datasets/LibreYOLO/circuit-elements) on HuggingFace

| Detail | Value |
|--------|-------|
| Images | 772 annotated images |
| Classes | 45 (breakers, contactors, relays, PLCs, fuses, terminals, transformers, etc.) |
| Format | YOLO (bounding box annotations) |
| License | CC BY 4.0 |
| Model | YOLOv11n (nano variant) |
| Framework | Ultralytics + PyTorch |

The training pipeline is implemented in `backend/training/train_yolo.py` with the dataset downloaded and ready. The pipeline supports configurable epochs, batch size, image size (640x640), and confidence/IoU thresholds.

## Installation & Setup

```bash
# Clone
git clone https://github.com/poojawork102/CabinetSight-AI-Project.git
cd CabinetSight-AI-Project

# Install dependencies
pip install -r requirements.txt

# Tesseract OCR binary (needed for pytesseract fallback)
# Windows: download installer from https://github.com/UB-Mannheim/tesseract/wiki
# Ubuntu:  sudo apt install tesseract-ocr

# Run
python run.py
```

Open `http://localhost:8000` in your browser.

## Generating Test Images

```bash
python backend/generate_test_images.py
```

Creates 5 synthetic cabinet panel sets in `assets/test-inputs/` with OCR-readable labels, coloured wires, and matching Excel/PDF files — producing a genuine mix of PASS, FAIL, and UNREADABLE results.

## CV Pipeline Details

- **Feature Matching:** ORB extracts ~1500 keypoints (Hamming distance), SIFT adds 128-D descriptors (L2 norm). BFMatcher with Lowe's ratio test (0.75) filters false positives. RANSAC computes homography.
- **OCR:** CLAHE contrast enhancement → EasyOCR (CRAFT detector + CRNN recogniser) → RapidFuzz fuzzy matching. Scores ≥80% = PASS, 40–80% = UNREADABLE, <40% = FAIL.
- **Colour Detection:** HSV range masking (primary) with K-means clustering (k=3) fallback. Supports 9 wire colours per IEC 60446.
- **Alignment:** Perspective homography (3x3 matrix) via RANSAC with SSIM quality scoring.

## Project Structure

```
QCSight/
├── index.html                  # Single-page frontend
├── src/
│   ├── app.js                  # UI logic, modals, backend integration
│   └── styles.css              # Dark/light theme, responsive layout
├── backend/
│   ├── api/routes.py           # FastAPI endpoints (/inspect, /inspect/demo)
│   ├── cv/
│   │   ├── inspector.py        # Main inspection orchestrator
│   │   ├── ocr_reader.py       # EasyOCR + Tesseract wrapper
│   │   └── color_analyzer.py   # HSV + K-means wire colour detection
│   ├── models/schemas.py       # Pydantic models (CheckResult, Verdict)
│   ├── training/train_yolo.py  # YOLOv11 training pipeline
│   └── generate_test_images.py # Synthetic test image generator
├── run.py                      # Uvicorn entry point
└── assets/test-inputs/         # Generated test sets
```

## Security & Privacy

- All processing runs **locally** — no data leaves the machine
- Zero telemetry, zero external API calls
- Input files are never persisted beyond the session

---

*Built for VIT Code Apex 3.0 — Emerson Problem Statement #03*
