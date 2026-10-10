# CabinetSight · Project Eagle Eye

A local, browser-based prototype for control-cabinet quality checks. Open `index.html` in VS Code or a browser; there is no build step, backend, telemetry, or external API.

## Run it

1. Open this folder in VS Code.
2. Open `index.html` in your browser (or use VS Code Live Server if installed).
3. Choose **Try demo data** to explore the review, evidence, re-check, history, and report flow. The evidence panel uses the cabinet QC example visual from the supplied Emerson problem statement.
4. For the upload path, select a cabinet JPG/PNG, GA PDF, wire list, and label list. The browser checks file extensions and enables the run button after all four are selected.

Inspection history is stored in the browser's `localStorage`. Use the same browser profile to see previous runs. **Export report** downloads an item-by-item CSV; it opens a print-ready report that can be saved as PDF from the browser's print dialog.

## Prototype boundary

The results are illustrative demo data, not the output of computer vision. The upload path demonstrates the interface and workflow; this prototype does not yet parse PDFs or spreadsheets, register photo-to-drawing geometry, detect devices, or read labels and ferrules. Do not use its findings for production QC. A real inspection engine should connect validated detection/OCR modules and parse the reference files before making any PASS/FAIL decision. In particular, it must preserve the SRS rule that uncertain text is UNREADABLE rather than guessed.

The re-check demo closes one previously failed item and retains another as open to demonstrate status tracking. The evidence boxes are sample locations; they are not model-generated detections.

## Layout

- `index.html` — interface and page structure
- `assets/cabinet-demo.png` — cabinet QC example cropped from the supplied problem statement
- `src/styles.css` — responsive visual design
- `src/app.js` — local interaction, sample run records, re-checks, history, CSV and printable report

## Declared tools

- Plain HTML, CSS and JavaScript; no third-party runtime packages or AI models.
- Browser `localStorage`, object URLs, CSV download, and print dialog.
- The UI uses system fonts and works offline.
