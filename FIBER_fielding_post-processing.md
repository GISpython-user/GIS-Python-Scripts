# FIBER Attachment & Photos Exporter (GUI)

A small PyQt6 GUI for extracting attachments (photos and other files) and exporting per-TL CSVs from a File Geodatabase (.gdb).

This README documents the included script `FIBER_Export_Attachments_Photos_Work - New_GUI_Date.py`, how to run it, its inputs/outputs, and common troubleshooting steps.

---

## Quick summary

- Purpose: Search a .gdb for the best-matching feature class and attachment table (fuzzy matching), optionally run a dry run to inspect counts, then export per-TL CSVs and extract attachments into a folder hierarchy.
- UI: Graphical (PyQt6) — prompts for: File Geodatabase, approx. Feature Class name, approx. Attachment Table name, Output folder, and a Dry Run checkbox.
- Important: The script depends on ArcGIS Pro's `arcpy` module; it must be run inside an ArcGIS Pro Python environment.

---

## Files

- `FIBER_Export_Attachments_Photos_Work - New_GUI_Date.py` — main GUI script (included in this repository).

---

## Contract / Behavior (short)

- Inputs: path to a File Geodatabase (.gdb), approximate names for a feature class and an attachment table (used for fuzzy matching), and an output folder.
- Outputs:
  - Extracted attachments saved under `<output>/<TL_Number>/<Structure_Number>/<attachment_file>`
  - Per-TL CSV files named like `<TL>_Fielding_MM_DD_YYYY.csv` in the output folder
  - If Dry Run is selected: `dry_run_report.txt` with the UI log
- Success criteria: Attachments written to output and CSVs exported. The UI logs progress and opens the output folder when finished.
- Error modes: invalid gdb path, inability to create output folder, fuzzy-match failures (no good match & score < 80), arcpy exceptions (permissions, data corruption), file-write errors.

---

## Requirements

- Windows or macOS/Linux (script has platform-specific folder-open logic).
- Python runtime with these packages available in the same environment that provides `arcpy` (ArcGIS Pro Python environment):
  - arcpy (ArcGIS Pro — not installable via pip)
  - rapidfuzz
  - PyQt6

Notes:
- `arcpy` is only available in ArcGIS Pro's Python environment. Run the script from ArcGIS Pro's Python prompt or a cloned conda environment that contains arcpy.
- Install pure-Python dependencies with pip in that same environment, for example:

```powershell
# Activate the ArcGIS Pro conda environment first (example names; use your environment name or the Python Command Prompt that ships with ArcGIS Pro)
# conda activate <your-arcgis-pro-env>
python -m pip install rapidfuzz PyQt6
```

---

## Usage

1. Launch the script from the ArcGIS Pro Python environment so `arcpy` is available. In PowerShell:

```powershell
# run from the project folder (adjust path as required)
python "FIBER_Export_Attachments_Photos_Work - New_GUI_Date.py"
```

2. GUI fields:
- File Geodatabase (.gdb): Use the Browse button to select the folder that ends with `.gdb`.
- Approx. Feature Class Name: A rough name for the feature class (fuzzy search will pick the best match).
- Approx. Attachment Table Name: A rough name for the attachment table (fuzzy search will pick the best match).
- Output Folder: Destination for CSVs and extracted attachments.
- Perform a dry run: If checked, the script will not write attachments; it will report counts and save `dry_run_report.txt`.

3. Click Run. Watch the UI log for progress and errors.

---

## Behavior details and notes

- Fuzzy matching: The script uses `rapidfuzz.process.extractOne` and requires a matching score >= 80 to accept a match. If the match score is below this threshold the script will abort and prompt an error.
- Dry-run: When selected, the script will record counts for the matched feature class and attachment table and save the UI log as `dry_run_report.txt` in the output folder. It will attempt to open the report in the system file browser and then exit.
- Coordinate system: The script temporarily sets an output coordinate system when calling `arcpy.management.AddXY` (WGS84 geographic). This step may fail on non-geographic data if some edge conditions occur.
- Output file naming: TL CSVs are named `<safe_TL>_Fielding_MM_DD_YYYY.csv`. The date uses the current system date.
- Attachment filenames: The script constructs filenames using the Structure_Number and original attachment name; it attempts to sanitize TL directory names to be alphanumeric, spaces, underscores, or hyphens.

---

## Output structure example

Output folder (example):

```
output/
  12345/
    6789/                      # Structure_Number
      6789 photo1.jpg
      6789_photo2.jpg
  23456/
    Unknown/
      attachment              # when Structure_Number missing
  12345_Fielding_03_04_2026.csv
  dry_run_report.txt         # if dry run performed
```

---

## Troubleshooting

- "Invalid geodatabase path": ensure you selected the `.gdb` folder (a File Geodatabase is a folder ending with `.gdb`).
- "No good match for feature class/table": try a different approximate name, or inspect the geodatabase directly with ArcGIS Pro to confirm layer/table names.
- `arcpy` import errors: run the script from ArcGIS Pro's Python environment (ArcGIS Pro Python Command Prompt or a conda environment cloned from the ArcGIS Pro base environment).
- Permission issues writing to output: choose a folder where you have write permissions (avoid protected system locations).
- Very large attachments: extraction writes file bytes directly; ensure sufficient disk space and consider processing a subset with the Dry Run first.

---

## Suggestions / Next steps (optional improvements)

- Add a progress bar and cancel button for long extractions.
- Make the fuzzy-match threshold configurable in the UI.
- Allow choosing whether to open the output folder at the end.
- Add filename sanitization for non-ASCII characters and duplicate-name handling.

---

## License

No license file is included — treat this as project-specific script. Add a LICENSE file if you want to publish with explicit terms.

---

If you'd like, I can also:
- Add a short unit test or a small non-arcpy stub harness for offline testing of the fuzzy matching and filename logic,
- Or add a brief `requirements.txt` specific to this script (excluding `arcpy`).

Tell me which of those you'd prefer and I'll add it.