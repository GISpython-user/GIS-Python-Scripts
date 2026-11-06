# -*- coding: utf-8 -*-
import os
import re
import shutil
import subprocess
import sys
import traceback
from collections import defaultdict
from datetime import datetime as DateTime

import arcpy
from PyQt6.QtCore import QEventLoop
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QMessageBox,
    QFileDialog,
)
from rapidfuzz import process


PHOTO_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
    ".heic",
    ".webp",
}


def format_text_table(headers, rows, highlighted_rows=None):
    """Render rows as a bordered, fixed-width text table."""
    highlighted_rows = highlighted_rows or set()
    formatted_rows = [
        [
            str(value)
            .replace("\r", " ")
            .replace("\n", " ")
            .replace("|", "/")
            for value in row
        ]
        for row in rows
    ]
    for index in highlighted_rows:
        if 0 <= index < len(formatted_rows) and formatted_rows[index]:
            formatted_rows[index][0] = "! " + formatted_rows[index][0]
            formatted_rows[index][-1] += " !"
    headers = [
        str(header).replace("\r", " ").replace("\n", " ").replace("|", "/")
        for header in headers
    ]
    widths = [
        max([len(headers[index])] + [len(row[index]) for row in formatted_rows])
        for index in range(len(headers))
    ]

    def format_row(row):
        return "| " + " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        ) + " |"

    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    table_lines = [border, format_row(headers), border]
    for row in formatted_rows:
        table_lines.extend([format_row(row), border])
    return table_lines


TL_PROJECTS_FOLDER = (
    r"C:\Users\ClarenceBodmer4L\OneDrive - 4Liberty\ArcGIS Pro Projects"
    r"\Projects\TL_Pro_projects"
)


class GeodatabaseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geodatabase FIBER Attachment Extractor")
        self._is_running = False
        self._task_completed = False

        # Layouts
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Input fields
        self.gdb_path = QLineEdit()
        self.fc_name = QLineEdit()
        self.table_name = QLineEdit()
        self.output_folder = QLineEdit()
        self.dry_run = QCheckBox("Perform a dry run")

        # Browse buttons
        self.gdb_browse = QPushButton("Browse...")
        self.gdb_browse.clicked.connect(self.pick_gdb)

        self.output_browse = QPushButton("Browse...")
        self.output_browse.clicked.connect(self.pick_output)

        form_layout.addRow("File Geodatabase (.gdb):", self.gdb_path)
        form_layout.addRow("", self.gdb_browse)
        form_layout.addRow("Approx. Feature Class Name:", self.fc_name)
        form_layout.addRow("Approx. Attachment Table Name:", self.table_name)
        form_layout.addRow("Output Folder:", self.output_folder)
        form_layout.addRow("", self.output_browse)
        form_layout.addRow(self.dry_run)

        # Buttons
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_process)

        # Output log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(2000)

        # Assemble layout
        layout.addLayout(form_layout)
        layout.addWidget(self.run_button)
        layout.addWidget(self.log)
        self.setLayout(layout)

    def log_message(self, msg):
        self.log.append(msg)
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def pick_gdb(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Geodatabase Folder")
        if folder:
            self.gdb_path.setText(folder)

    def pick_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder.setText(folder)

    def run_process(self):
        if self._is_running:
            return

        self._is_running = True
        self._task_completed = False
        controls = (
            self.gdb_path,
            self.fc_name,
            self.table_name,
            self.output_folder,
            self.dry_run,
            self.gdb_browse,
            self.output_browse,
            self.run_button,
        )
        for control in controls:
            control.setEnabled(False)
        try:
            self._run_process()
        except Exception as e:
            details = traceback.format_exc()
            self.log_message(f"❌ Processing stopped unexpectedly: {e}\n{details}")
            QMessageBox.critical(self, "Processing Error", str(e))
        finally:
            self._is_running = False
            for control in controls:
                control.setEnabled(True)
            if self._task_completed:
                self.close()

    def closeEvent(self, event):
        if self._is_running:
            event.ignore()
            self.log_message("Processing is still running; wait for it to finish before closing.")
            return
        super().closeEvent(event)

    def _run_process(self):
        gdb_path = self.gdb_path.text().strip()
        approx_fc_name = self.fc_name.text().strip()
        approx_table_name = self.table_name.text().strip()
        output_folder = self.output_folder.text().strip()
        dry_run = self.dry_run.isChecked()

        # Validate paths
        if not os.path.isdir(gdb_path) or not gdb_path.endswith(".gdb"):
            QMessageBox.critical(self, "Error", f"Invalid geodatabase path: {gdb_path}")
            return

        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
                self.log_message(f"📁 Output folder was created: {output_folder}")
            except Exception as e:
                QMessageBox.critical(
                    self, "ERROR", f"Failed to create the output folder: {e}"
                )
                return

        # List contents
        arcpy.env.workspace = gdb_path
        feature_classes = arcpy.ListFeatureClasses()
        tables = arcpy.ListTables()

        best_fc = process.extractOne(approx_fc_name, feature_classes)
        best_table = process.extractOne(approx_table_name, tables)

        if not best_fc or best_fc[1] < 80:
            QMessageBox.critical(
                self, "ERROR", f"No good match for feature class '{approx_fc_name}'"
            )
            return
        if not best_table or best_table[1] < 80:
            QMessageBox.critical(
                self, "ERROR", f"No good match for attachment table '{approx_table_name}'"
            )
            return

        feature_class = os.path.join(gdb_path, best_fc[0])
        attachment_table = os.path.join(gdb_path, best_table[0])
        self.log_message(
            f"✅ Matched feature class: {best_fc[0]} (Score: {best_fc[1]})"
        )
        self.log_message(
            f"✅ Matched attachment table: {best_table[0]} (Score: {best_table[1]})"
        )

        # Generate the report on every run before any export or attachment changes.
        report_lines = [
            "FIBER ATTACHMENT EXPORT - PRE-RUN REPORT",
            "=" * 40,
            f"Generated: {DateTime.now().astimezone().isoformat(timespec='seconds')}",
            f"Mode: {'Dry run; no export processing will follow.' if dry_run else 'Full run; export processing will follow.'}",
            f"Geodatabase: {gdb_path}",
            f"Feature class: {best_fc[0]} (match score: {best_fc[1]})",
            f"Attachment table: {best_table[0]} (match score: {best_table[1]})",
            f"Output folder: {output_folder}",
            (
                "Only this report is written; exports and attachment extraction are skipped."
                if dry_run
                else "This report is written before the normal export process begins. "
                     "The full run may modify geodatabase data and create output files."
            ),
            "",
            "RECORD COUNTS",
            "--------------",
        ]

        try:
            fc_count = int(arcpy.management.GetCount(feature_class)[0])
            report_lines.extend(
                format_text_table(
                    ["Record source", "Record count"],
                    [["Feature class", str(fc_count)]],
                )
            )
        except Exception as e:
            report_lines.append(f"ERROR: Could not count feature class records: {e}")

        try:
            tbl_count = int(arcpy.management.GetCount(attachment_table)[0])
            report_lines.extend(
                format_text_table(
                    ["Record source", "Record count"],
                    [["Attachment table", str(tbl_count)]],
                )
            )
        except Exception as e:
            report_lines.append(f"ERROR: Could not count attachment table records: {e}")

        feature_globalids = set()
        attachment_counts = defaultdict(int)
        feature_records_by_tl = defaultdict(int)
        attachments_by_tl = defaultdict(int)
        empty_rel_globalid_count = 0
        attachment_relationships_read = False

        try:
            attachment_fields = {
                field.name.casefold(): field.name
                for field in arcpy.ListFields(attachment_table)
            }
            rel_globalid_field = attachment_fields.get("rel_globalid")
            if not rel_globalid_field:
                report_lines.append(
                    "ERROR: Attachment table has no REL_GLOBALID field; "
                    "per-record attachment counts cannot be calculated."
                )
            else:
                with arcpy.da.SearchCursor(
                        attachment_table, [rel_globalid_field]
                ) as cursor:
                    for (rel_globalid,) in cursor:
                        if rel_globalid:
                            normalized_id = (
                                str(rel_globalid).strip().strip("{}").casefold()
                            )
                            attachment_counts[normalized_id] += 1
                        else:
                            empty_rel_globalid_count += 1
                attachment_relationships_read = True
        except Exception as e:
            report_lines.append(f"ERROR: Could not read attachment relationships: {e}")

        report_lines.extend(
            [
                "",
                "ATTACHMENTS PER FEATURE RECORD",
                "-------------------------------",
            ]
        )

        feature_records_read = False
        feature_table_rows = []
        highlighted_feature_rows = set()
        feature_table_headers = None
        try:
            feature_fields = {
                field.name.casefold(): field.name
                for field in arcpy.ListFields(feature_class)
            }
            globalid_field = feature_fields.get("globalid")
            if not globalid_field:
                report_lines.append(
                    "ERROR: Feature class has no GlobalID field; "
                    "per-record attachment counts cannot be calculated."
                )
            else:
                detail_fields = [
                    feature_fields[name]
                    for name in (
                        "structure_number",
                        "tl_number",
                        "date_fielded",
                    )
                    if name in feature_fields
                ]
                cursor_fields = [globalid_field] + detail_fields
                structure_field_index = (
                    1 + detail_fields.index(feature_fields["structure_number"])
                    if "structure_number" in feature_fields
                    else None
                )
                tl_field_index = (
                    1 + detail_fields.index(feature_fields["tl_number"])
                    if "tl_number" in feature_fields
                    else None
                )
                report_lines.append(
                    "Each row lists expected linked attachments. In dry-run mode, "
                    "existing photos are checked in the record's output folder; rows "
                    "with fewer photos than expected are enclosed by exclamation marks."
                )
                feature_table_headers = (
                    ["Record #", "GlobalID"]
                    + detail_fields
                    + ["Expected attachments"]
                )
                if dry_run:
                    feature_table_headers += ["Existing photos", "Photo check"]
                records_with_attachments = 0
                records_without_attachments = 0

                with arcpy.da.SearchCursor(feature_class, cursor_fields) as cursor:
                    for record_number, row in enumerate(cursor, start=1):
                        globalid = row[0]
                        normalized_id = (
                            str(globalid).strip().strip("{}").casefold()
                            if globalid
                            else ""
                        )
                        if normalized_id:
                            feature_globalids.add(normalized_id)
                        count = attachment_counts.get(normalized_id, 0)
                        if tl_field_index is not None and row[tl_field_index]:
                            tl_value = str(row[tl_field_index])
                            feature_records_by_tl[tl_value] += 1
                            attachments_by_tl[tl_value] += count
                        if count:
                            records_with_attachments += 1
                        else:
                            records_without_attachments += 1

                        values = [
                            (
                                str(value)
                                .replace("\r", " ")
                                .replace("\n", " ")
                                .replace("|", "/")
                                if value is not None
                                else ""
                            )
                            for value in row[1:]
                        ]
                        record_values = (
                            [str(record_number), str(globalid or "")]
                            + values
                            + [str(count)]
                        )
                        highlight_row = False
                        if dry_run:
                            if (
                                tl_field_index is not None
                                and structure_field_index is not None
                                and row[tl_field_index]
                                and row[structure_field_index]
                            ):
                                photo_folder = os.path.join(
                                    output_folder,
                                    str(row[tl_field_index]),
                                    str(row[structure_field_index]),
                                )
                                try:
                                    existing_photos = sum(
                                        1
                                        for entry in os.scandir(photo_folder)
                                        if entry.is_file()
                                        and os.path.splitext(entry.name)[1].casefold()
                                        in PHOTO_EXTENSIONS
                                    )
                                    existing_photo_text = str(existing_photos)
                                    if existing_photos < count:
                                        photo_check = (
                                            f"SHORT: {existing_photos}/{count}"
                                        )
                                        highlight_row = True
                                    else:
                                        photo_check = f"OK: {existing_photos}/{count}"
                                except FileNotFoundError:
                                    existing_photo_text = "0"
                                    if count:
                                        photo_check = f"SHORT: 0/{count}"
                                        highlight_row = True
                                    else:
                                        photo_check = "OK: 0/0"
                                except OSError as e:
                                    existing_photo_text = f"ERROR: {e}"
                                    photo_check = "CHECK ERROR"
                            else:
                                existing_photo_text = "N/A"
                                photo_check = "N/A (missing TL/Structure)"
                            record_values.extend(
                                [existing_photo_text, photo_check]
                            )
                        feature_table_rows.append(record_values)
                        if highlight_row:
                            highlighted_feature_rows.add(
                                len(feature_table_rows) - 1
                            )
                feature_records_read = True

                report_lines.extend(
                    [
                        "",
                        f"Feature records with attachments: {records_with_attachments}",
                        f"Feature records without attachments: {records_without_attachments}",
                    ]
                )
        except Exception as e:
            feature_records_read = False
            report_lines.append(f"ERROR: Could not list feature records: {e}")

        if feature_table_headers:
            report_lines.extend(
                format_text_table(
                    feature_table_headers,
                    feature_table_rows,
                    highlighted_feature_rows,
                )
            )

        if attachment_relationships_read and feature_records_read:
            linked_attachment_rows = sum(
                count
                for globalid, count in attachment_counts.items()
                if globalid in feature_globalids
            )
            unmatched_attachment_rows = sum(
                count
                for globalid, count in attachment_counts.items()
                if globalid not in feature_globalids
            )
            report_lines.extend(
                [
                    "",
                    "ATTACHMENT RELATIONSHIP SUMMARY",
                    "-------------------------------",
                ]
            )
            report_lines.extend(
                format_text_table(
                    ["Relationship status", "Attachment rows"],
                    [
                        ["Linked to a feature record", str(linked_attachment_rows)],
                        ["Unmatched REL_GLOBALID", str(unmatched_attachment_rows)],
                        ["Empty REL_GLOBALID", str(empty_rel_globalid_count)],
                    ],
                )
            )
        else:
            report_lines.extend(
                [
                    "",
                    "ATTACHMENT RELATIONSHIP SUMMARY",
                    "-------------------------------",
                    "Not available because the attachment or feature relationship fields "
                    "could not be read completely. Check Data Quality for Errors in the geodatabase.",
                ]
            )

        report_lines.extend(
            [
                "",
                "REPORT SCOPE AND NEXT ACTION",
                "-------------",
                "The script matched the requested feature class and attachment table, "
                "counted their records, and inspected GlobalID/REL_GLOBALID relationships.",
                (
                    "Dry run selected: the script stops after writing this report; no coordinates, "
                    "Excel files, joins, attachment folders, or attachment files are created."
                    if dry_run
                    else "Dry run not selected: after writing this report, the script continues with "
                         "coordinate updates, Excel exports, field joins, and attachment extraction."
                ),
            ]
        )
        if dry_run:
            report_lines.extend(
                [
                    "",
                    "POST-PROCESSING ATTACHMENT RESULTS",
                    "-----------------------------------",
                    "Attachments successfully saved: 0 (attachment extraction was skipped).",
                    "No attachment folders were created or inspected for photo counts.",
                ]
            )

        report_path = os.path.join(output_folder, "dry_run_report.txt")
        report_saved = False
        self.log_message(
            f"Pre-run report prepared: {len(feature_globalids)} unique feature GlobalIDs; "
            f"{sum(attachment_counts.values())} attachment rows have a REL_GLOBALID."
        )
        try:
            with open(report_path, "w", encoding="utf-8") as rpt:
                rpt.write("\n".join(report_lines) + "\n")
            report_saved = True
            self.log_message(f"📄 Pre-run report saved to: {report_path}")
        except Exception as e:
            self.log_message(f"⚠️ Could not save the pre-run report: {e}")

        if dry_run:
            # Dry runs report expected counts without creating export or attachment files.
            tl_values = sorted(feature_records_by_tl, key=str.casefold)
            if tl_values:
                used_report_names = set()
                for tl_index, tl in enumerate(tl_values, start=1):
                    safe_tl = (
                            "".join(
                                ch
                                for ch in str(tl)
                                if ch.isalnum() or ch in ("_", "-", " ")
                            ).strip()
                            or "Unknown_TL"
                    )
                    report_name = f"dry_run_report_TL_{safe_tl}.txt"
                    if report_name.casefold() in used_report_names:
                        report_name = f"dry_run_report_TL_{safe_tl}_{tl_index}.txt"
                    used_report_names.add(report_name.casefold())
                    tl_report_path = os.path.join(output_folder, report_name)

                    tl_folder = os.path.join(output_folder, str(tl))
                    photo_count_text = "Not counted"
                    if os.path.isdir(tl_folder):
                        try:
                            photo_count = sum(
                                1
                                for root, _, files in os.walk(tl_folder)
                                for filename in files
                                if os.path.splitext(filename)[1].casefold()
                                in {
                                    ".jpg",
                                    ".jpeg",
                                    ".png",
                                    ".gif",
                                    ".tif",
                                    ".tiff",
                                    ".bmp",
                                    ".heic",
                                    ".webp",
                                }
                            )
                            photo_count_text = str(photo_count)
                        except OSError as e:
                            photo_count_text = f"ERROR: {e}"

                    tl_lines = [
                        "TL DRY RUN REPORT",
                        "================",
                        f"Generated: {DateTime.now().astimezone().isoformat(timespec='seconds')}",
                        f"TL: {tl}",
                        f"Output Folder: {output_folder}",
                        "",
                        "RECORD SUMMARY",
                        "--------------",
                        *format_text_table(
                            ["Feature records", "Expected attachments"],
                            [[
                                str(feature_records_by_tl[tl]),
                                str(attachments_by_tl[tl]),
                            ]],
                        ),
                        "",
                        "OUTPUT FOLDERS AND PHOTO COUNTS",
                        "------------------------------",
                        *format_text_table(
                            [
                                "Line #",
                                "Expected output folder",
                                "Expected attachments",
                                "Existing photo files",
                            ],
                            [[
                                "1",
                                tl_folder,
                                str(attachments_by_tl[tl]),
                                photo_count_text,
                            ]],
                        ),
                        "",
                        "ATTACHMENT PROCESSING DETAILS",
                        "-----------------------------",
                        "Attachment extraction was intentionally skipped in dry-run mode.",
                        "No attachments were written; there are no processing failures to report.",
                    ]
                    try:
                        with open(tl_report_path, "w", encoding="utf-8") as rpt:
                            rpt.write("\n".join(tl_lines) + "\n")
                        self.log_message(
                            f"📄 TL dry run report saved: {tl_report_path}"
                        )
                    except Exception as e:
                        self.log_message(f"⚠️ Could not save TL dry run report: {e}")
            else:
                self.log_message(
                    "No TL project names were identified. Dry run report remains in the main summary file."
                )

            try:
                if report_saved:
                    if os.name == "nt":
                        subprocess.run(
                            ["explorer", "/select,", report_path], check=False
                        )
                    elif sys.platform == "darwin":
                        subprocess.run(["open", "-R", report_path], check=False)
                    else:
                        folder = os.path.dirname(report_path) or "."
                        subprocess.run(["xdg-open", folder], check=False)
                    self.log_message(f"📂 Opened the folder containing: {report_path}")
            except Exception as e:
                self.log_message(f"⚠️ Could not open folder: {e}")

            self.log_message(
                "Dry run is complete. No export or attachment processing was performed."
            )
            self._task_completed = True
            return

        # Step 7: Allow overwriting
        arcpy.env.overwriteOutput = True

        # Step 8: Add X,Y coordinates
        try:
            with arcpy.EnvManager(
                    outputCoordinateSystem="GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]"
            ):
                updated_features = arcpy.management.AddXY(feature_class)[0]
            self.log_message("✅ X,Y coordinates successfully added")
        except Exception as e:
            self.log_message(f"⚠️ Failed to add the X,Y coordinates: {e}")
            return

        # Step 9: Export tables by TL_Number
        tl_numbers = set()
        with arcpy.da.SearchCursor(updated_features, ["TL_Number"]) as cursor:
            for row in cursor:
                if row[0]:
                    tl_numbers.add(str(row[0]))

        for tl in tl_numbers:
            where_clause = f"TL_Number = '{tl}'"
            layer_name = f"layer_{tl}"
            arcpy.management.MakeFeatureLayer(
                updated_features, layer_name, where_clause
            )

            # Build a safe folder/name for the TL
            safe_tl = "".join(
                c for c in tl if c.isalnum() or c in (" ", "_", "-")
            ).rstrip()

            # Attempt to get Date_Fielded from the features in this TL group and use it in the filename.
            # Fall back to the current date if no valid Date_Fielded is found.
            date_str = DateTime.now().strftime("%m_%d_%Y")  # default
            try:
                date_val = None
                with arcpy.da.SearchCursor(layer_name, ["Date_Fielded"]) as date_cursor:
                    for r in date_cursor:
                        if r and r[0]:
                            date_val = r[0]
                            break

                if date_val:
                    # If it's already a datetime, format directly
                    if isinstance(date_val, DateTime):
                        date_str = date_val.strftime("%m_%d_%Y")
                    else:
                        # Try ISO parse first, then sanitize as a fallback
                        try:
                            parsed = DateTime.fromisoformat(str(date_val))
                            date_str = parsed.strftime("%m_%d_%Y")
                        except Exception:
                            s = str(date_val)
                            # Replace common separators with underscores and remove extra whitespace
                            s = (
                                s.strip()
                                .replace("/", "_")
                                .replace("-", "_")
                                .replace(" ", "_")
                            )
                            # Keep only safe characters (alnum and underscore)
                            s = "".join(ch for ch in s if ch.isalnum() or ch == "_")
                            if s:
                                date_str = s
            except Exception as e:
                self.log_message(
                    f"⚠️ Could not read the Date Fielded column for TL {tl}: {e}"
                )

            excel_output = os.path.join(
                output_folder, f"{safe_tl}_FIBER_Field_Survey_{date_str}.xlsx"
            )

            try:
                arcpy.conversion.TableToExcel(
                    Input_Table=layer_name, Output_Excel_File=excel_output
                )

                self.log_message(f"✅ Exported Excel table to: {excel_output}")
                survey_folder = os.path.join(
                    TL_PROJECTS_FOLDER, safe_tl, "Field_Veg_Surveys"
                )
                os.makedirs(survey_folder, exist_ok=True)
                survey_copy = os.path.join(survey_folder, os.path.basename(excel_output))
                shutil.copy2(excel_output, survey_copy)
                self.log_message(f"✅ Copied Excel table to: {survey_copy}")

            except Exception as e:
                self.log_message(
                    f"⚠️ Failed to export or copy Excel file for TL {tl}: {e}"
                )

            finally:
                arcpy.management.Delete(layer_name)

        # Step 10: Join fields
        try:
            arcpy.management.JoinField(
                in_data=attachment_table,
                in_field="REL_GLOBALID",
                join_table=feature_class,
                join_field="GlobalID",
                fields=["Structure_Number", "Scope_of_Work", "TL_Number", "Date_Fielded"],
            )
            self.log_message("✅ Fields joined successfully")
        except Exception as e:
            self.log_message(f"⚠️ Failed to join fields: {e}")

        # Step 11: Extract attachments
        attachment_rows_attempted = 0
        attachment_rows_saved = 0
        attachment_rows_failed = 0
        attachments_by_folder = defaultdict(int)
        attachment_folders = set()
        attachment_extraction_complete = False
        attachment_extraction_error = None
        attachment_failures = []

        try:
            with arcpy.da.SearchCursor(
                    attachment_table,
                    ["DATA", "ATT_NAME", "ATTACHMENTID", "Structure_Number", "TL_Number"],
            ) as cursor:
                for item in cursor:
                    attachment_rows_attempted += 1
                    attachment = item[0]
                    # Build structure and attachment name parts separately so we only pad numbers in the attachment filename
                    att_orig = str(item[1]) if item[1] else ""
                    struct_part = str(item[3]) if item[3] else ""

                    # Pad single-digit trailing numbers in the attachment base name (1-9 -> 01-09)
                    try:
                        base, ext = os.path.splitext(att_orig)
                        if base:
                            m = re.search(r"(\d+)$", base)
                            if m and len(m.group(1)) == 1:
                                # replace the trailing single digit with zero-padded version
                                base = base[: m.start(1)] + m.group(1).zfill(2)
                        att_part = base + ext
                    except Exception:
                        att_part = att_orig

                    # Combine pole number and attachment part (if present)
                    if struct_part and att_part:
                        att_name = f"{struct_part} {att_part}"
                    else:
                        att_name = att_part or struct_part or "attachment"

                    structure_num = struct_part if struct_part else "Unknown"
                    tl_number = str(item[4]) if item[4] else "Unknown"

                    tl_folder = os.path.join(output_folder, f"{tl_number}")
                    structure_folder = os.path.join(tl_folder, structure_num)
                    file_path = os.path.join(structure_folder, att_name)
                    try:
                        if attachment is None:
                            raise ValueError("attachment data is empty")
                        os.makedirs(tl_folder, exist_ok=True)
                        os.makedirs(structure_folder, exist_ok=True)
                        with open(file_path, "wb") as f:
                            f.write(attachment.tobytes())
                        attachment_rows_saved += 1
                        attachments_by_folder[structure_folder] += 1
                        attachment_folders.add(structure_folder)
                        if attachment_rows_saved % 25 == 0:
                            self.log_message(
                                f"✅ Saved {attachment_rows_saved} attachments; "
                                f"most recent: {file_path}"
                            )
                    except Exception as e:
                        attachment_rows_failed += 1
                        attachment_failures.append(
                            {
                                "tl": tl_number,
                                "structure": structure_num,
                                "file": att_name,
                                "attachment_id": item[2],
                                "reason": str(e),
                            }
                        )
                        self.log_message(f"⚠️ Failed to save {att_name}: {e}")
            attachment_extraction_complete = True
        except Exception as e:
            attachment_extraction_error = e
            attachment_failures.append(
                {
                    "tl": "Unknown",
                    "structure": "Unknown",
                    "file": "Attachment cursor",
                    "attachment_id": "Unknown",
                    "reason": f"Could not read attachment records: {e}",
                }
            )
            self.log_message(f"⚠️ Failed to extract attachments: {e}")

        attachment_result_lines = [
            "",
            "POST-PROCESSING ATTACHMENT RESULTS",
            "-----------------------------------",
            f"Attachment rows attempted: {attachment_rows_attempted}",
            f"Attachments successfully saved: {attachment_rows_saved}",
            f"Attachment saves failed: {attachment_rows_failed}",
            f"Attachment extraction completed: {'Yes' if attachment_extraction_complete else 'No'}",
        ]
        if attachment_extraction_error:
            attachment_result_lines.append(
                f"Attachment extraction error: {attachment_extraction_error}"
            )

        if attachment_folders:
            attachment_result_lines.extend(
                [
                    "",
                    "OUTPUT FOLDERS AND PHOTO COUNTS",
                    "--------------------------------",
                ]
            )
            folder_rows = []
            for index, folder in enumerate(
                    sorted(attachment_folders, key=str.casefold), start=1
            ):
                try:
                    photo_count = sum(
                        1
                        for entry in os.scandir(folder)
                        if entry.is_file()
                        and os.path.splitext(entry.name)[1].casefold()
                        in PHOTO_EXTENSIONS
                    )
                    photo_count_text = str(photo_count)
                except Exception as e:
                    photo_count_text = f"ERROR: {e}"
                folder_rows.append(
                    [
                        str(index),
                        folder,
                        str(attachments_by_folder[folder]),
                        photo_count_text,
                    ]
                )
            attachment_result_lines.extend(
                format_text_table(
                    [
                        "Line #",
                        "Folder",
                        "Attachments saved this run",
                        "Photo files present",
                    ],
                    folder_rows,
                )
            )
        else:
            attachment_result_lines.extend(
                [
                    "",
                    "No attachment folders received successfully saved attachments during this run.",
                ]
            )

        attachment_result_lines.extend(
            [
                "",
                "UNSUCCESSFUL ATTACHMENT PROCESSING DETAILS",
                "----------------------------------------",
            ]
        )
        if attachment_failures:
            attachment_result_lines.extend(
                format_text_table(
                    [
                        "Line #",
                        "TL",
                        "Structure",
                        "Attachment ID",
                        "File",
                        "Reason",
                    ],
                    [
                        [
                            str(index),
                            failure["tl"],
                            failure["structure"],
                            str(failure["attachment_id"]),
                            failure["file"],
                            failure["reason"],
                        ]
                        for index, failure in enumerate(attachment_failures, start=1)
                    ],
                )
            )
        else:
            attachment_result_lines.append(
                "No unsuccessful attachments were recorded during this run."
            )

        for line in attachment_result_lines:
            self.log_message(line)
        try:
            with open(report_path, "a", encoding="utf-8") as rpt:
                rpt.write("\n".join(attachment_result_lines) + "\n")
            self.log_message(f"📄 Final attachment results are appended to: {report_path}")
        except Exception as e:
            self.log_message(
                f"⚠️ Could not append the attachment results to the report: {e}"
            )

        # Open output folder
        try:
            if os.name == "nt":
                os.startfile(output_folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", output_folder], check=False)
            else:
                subprocess.run(["xdg-open", output_folder], check=False)
            self.log_message(f"📂 Opened the output folder: {output_folder}")
        except Exception as e:
            self.log_message(f"⚠️ Could not open the output folder: {e}")

        self.log_message("✅ Process completed successfully")
        self._task_completed = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeodatabaseApp()
    window.resize(700, 500)
    window.show()
    sys.exit(app.exec())
