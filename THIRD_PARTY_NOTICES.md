# Third-party notices

CabinetSight's own code is MIT-licensed (see `LICENSE`). It depends on third-party
software and data that keep their own licences:

| Component | Used for | Licence |
|-----------|----------|---------|
| OpenCV (opencv-python-headless) | Feature matching, homography, colour analysis | Apache-2.0 |
| EasyOCR | Label / ferrule OCR | Apache-2.0 |
| Tesseract / pytesseract | Fallback OCR | Apache-2.0 |
| RapidFuzz | Fuzzy text matching | MIT |
| scikit-learn | K-means wire-colour clustering | BSD-3-Clause |
| FastAPI, Uvicorn, Pydantic | Backend API | MIT / BSD-3-Clause |
| openpyxl | Excel wire/label lists | MIT |
| ReportLab | PDF generation | BSD |
| PyMuPDF | Rendering the GA drawing PDF (planned) | AGPL-3.0 (or commercial licence) |
| Ultralytics YOLO | Optional training script only (`backend/training/`), not used in inspection | AGPL-3.0 (or commercial licence) |
| LibreYOLO/circuit-elements dataset | Optional training data (not included in this repo) | CC BY 4.0 |

Problem statement and example faults: Emerson PS #03, VIT Code Apex 3.0 (AISF, VIT Pune).

Note: AGPL-3.0 components (PyMuPDF, Ultralytics) are fine for this open hackathon project. Any
commercial or closed-source deployment must replace them (e.g. pypdfium2, an Apache-2.0 detector)
or obtain a commercial licence.
