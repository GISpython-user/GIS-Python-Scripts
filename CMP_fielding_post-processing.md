# Geodatabase Attachment Extractor

A small GUI tool that extracts attachments from a File Geodatabase attachment table, joins selected fields from the related feature class, exports per-TL CSVs, and saves attachment files organized by TL and structure. The script uses fuzzy matching to find the target feature class and attachment table inside a .gdb and provides a simple Qt-based interface for interaction.

## Requirements

- ArcGIS Pro (provides `arcpy`) — run the script from ArcGIS Pro's `arcgispro-py3` environment.
- Python (use the version bundled with your ArcGIS Pro install).
- rapidfuzz — `pip install rapidfuzz`
- PyQt6 — `pip install PyQt6`

Note: `arcpy` is provided by ArcGIS Pro and should not be installed with pip.

## Installation / Activation

1. Open the "Python Command Prompt (ArcGIS Pro)" or activate the ArcGIS Pro conda environment:

   conda activate arcgispro-py3
   pip install rapidfuzz PyQt6

2. Place `CMP_Export_Attachments_Photos_Work - New_GUI_Date.py` in a folder you can run from, or run it directly from the ArcGIS Pro environment.

## Usage (GUI fields)

- File Geodatabase (.gdb): Browse to or paste the folder path that contains the `.gdb` (folder path ending in `.gdb`).
- Approx. Feature Class Name: Enter a fragment of the feature class name; fuzzy matching selects the best match.
- Approx. Attachment Table Name: Enter a fragment of the attachment table name; fuzzy matching selects the best match.
- Output Folder: Destination for CSV exports and extracted attachments.
- Perform a dry run: If checked, the tool reports counts and exits without writing files.
- Run: Start extraction. Progress and messages appear in the log pane.

## Example command

Run from the ArcGIS Pro Python prompt:

python "CMP_Export_Attachments_Photos_Work - New_GUI_Date.py"

## Output structure

- CSVs: saved in the output folder as `{TL}_CMP_Fielding_{MM_DD_YYYY}.csv`.
- Attachments: saved under `output_folder/{TL}/{StructureNumber}/{AttachmentFileName}`.

## Troubleshooting

- "No module named arcpy": ensure you run inside ArcGIS Pro's Python environment.
- Fuzzy-match failures or low scores: try entering a clearer name fragment or inspect feature/table names with ArcGIS tools.
- Permission errors writing files: check folder permissions, antivirus, or file locks.
- Large attachments: ensure enough disk space; consider extracting a subset.

## Security & Notes

Attachments may contain sensitive data. Run with appropriate access rights and follow your organization's data-handling policies. The script sanitizes file names but review output before sharing.

## Changelog

- v0.1 — Initial release: fuzzy matching, CSV export, attachment extraction.

## Repository checklist

- `CMP_Export_Attachments_Photos_Work - New_GUI_Date.py` (main script)
- `README.md` (this file)
- `requirements.txt` (optional: rapidfuzz, PyQt6)
- `LICENSE` (optional)

Author: Replace with your name/contact