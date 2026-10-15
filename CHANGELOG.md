# Changelog

All notable changes to CabinetSight — Project EAGLE EYE.

---

## Prototype

### v0.2.1 — 2026-10-16
- **Re-check flow**: demo re-check now closes all FAIL items as CLOSED and verifies UNREADABLE items (was: only 1 item closed)
- **Backend re-check**: re-check now uses the CV pipeline when backend is running (was: always fell back to demo)
- **Report export**: added summary stats, suggested corrective actions, confidence threshold, and professional styling
- **Evidence scaling**: added ResizeObserver so photo markers reposition on window resize and image load
- **Known limitations**: updated README to reflect current state

### v0.2.0 — 2026-10-15
- **Presentation fixes (Parts A-E)**: aligned all UI text with deck/PRD
- **No-false-FAIL enforcement**: uncertain verdicts → UNREADABLE, never FAIL; 5 pytest tests
- **IEC 60446 → 60445**: corrected standard reference across backend and frontend
- **Hero orbital workflow**: 5-step workflow animation around 3D cabinet
- **Removed Architecture section**: streamlined for hackathon demo
- **Tech section**: retitled to "Current Prototype Stack", replaced YOLO card with FastAPI

### v0.1.1 — 2026-10-14
- Backend, requirements.txt, .gitignore added to repo
- Clone URL fixed; YOLO11 labels, epoch count corrected in training script
- README rewritten for hackathon: current prototype + Round 2 plan

### v0.1.0 — 2026-10-13
- Favicon, README, feature detail modals, architecture section
- Hero spacing reduced

### v0.0.1 — 2026-10-12
- Initial prototype: HTML/CSS/JS frontend, upload UI, demo QC checklist, photo evidence, run history, CSV export

---

## Presentation Deck

### Final (v3) — 2026-10-15
- 8 slides: problem → solution → features/UI → architecture → roadmap → impact
- Honest "Built today" vs "Round 2" vs "Finale" roadmap on slide 6
- UI screenshot from live prototype on slide 5
- Tech stack split: current prototype (ORB/SIFT, EasyOCR, FastAPI) vs Round 2 targets (YOLO, PaddleOCR, Docker)

### v2 — 2026-10-14
- Added implementation roadmap slide
- Updated tech stack to separate current vs planned

### v1 — 2026-10-13
- Initial deck: problem statement, proposed solution, architecture, team

---

## PRD (Product Requirements Document)

### v1.2 — 2026-10-15
- 64 EARS requirements (FR-01 through FR-91, NFR-01 through NFR-15)
- Solution architecture: 5-stage pipeline (Input → Perceive → Match → Verdict Gate → Report & Re-check)
- MoSCoW scope by delivery stage
- Data model: QCCheck protocol, REST API spec
- Verdict policy: PASS / FAIL / UNREADABLE / CLOSED / NOT_AUTOMATED
- Test strategy, sustainability section, risk register, delivery calendar
- NFR-07: no data off machine, no telemetry, no organiser data in public repo

### v1.1 — 2026-10-14
- Added MoSCoW scope breakdown per round
- Expanded NFRs to 15 items
- Added risk register and delivery calendar

### v1.0 — 2026-10-13
- Initial PRD: 48 requirements, architecture overview, basic API spec
