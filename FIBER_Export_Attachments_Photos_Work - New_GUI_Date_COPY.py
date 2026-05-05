# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import arcpy
import re
from datetime import datetime
from rapidfuzz import process
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QCheckBox, QTextEdit, QMessageBox, QFileDialog
)


class GeodatabaseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geodatabase Attachment Extractor")

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

        # Assemble layout
        layout.addLayout(form_layout)
        layout.addWidget(self.run_button)
        layout.addWidget(self.log)
        self.setLayout(layout)

    def log_message(self, msg):
        self.log.append(msg)
        QApplication.processEvents()

    def pick_gdb(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Geodatabase Folder")
        if folder:
            self.gdb_path.setText(folder)

    def pick_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder.setText(folder)

    def run_process(self):
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
                self.log_message(f"📁 Output folder created: {output_folder}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create output folder: {e}")
                return

        # List contents
        arcpy.env.workspace = gdb_path
        feature_classes = arcpy.ListFeatureClasses()
        tables = arcpy.ListTables()

        best_fc = process.extractOne(approx_fc_name, feature_classes)
        best_table = process.extractOne(approx_table_name, tables)

        if not best_fc or best_fc[1] < 80:
            QMessageBox.critical(self, "Error", f"No good match for feature class '{approx_fc_name}'")
            return
        if not best_table or best_table[1] < 80:
            QMessageBox.critical(self, "Error", f"No good match for table '{approx_table_name}'")
            return

        feature_class = os.path.join(gdb_path, best_fc[0])
        attachment_table = os.path.join(gdb_path, best_table[0])
        self.log_message(f"✅ Matched feature class: {best_fc[0]} (Score: {best_fc[1]})")
        self.log_message(f"✅ Matched attachment table: {best_table[0]} (Score: {best_table[1]})")

        # Dry run report
        if dry_run:
            self.log_message("\n🔎 DRY RUN REPORT (no changes will be made)\n")
            try:
                fc_count = int(arcpy.management.GetCount(feature_class)[0])
                tbl_count = int(arcpy.management.GetCount(attachment_table)[0])
                self.log_message(f"Feature class record count: {fc_count}")
                self.log_message(f"Attachment table record count: {tbl_count}")
            except Exception as e:
                self.log_message(f"Could not get counts: {e}")

            # Save the log to a persistent file
            try:
                report_path = os.path.join(output_folder, "dry_run_report.txt")
                with open(report_path, "w", encoding="utf-8") as rpt:
                    rpt.write(self.log.toPlainText())
                self.log_message(f"📄 Dry run saved to: {report_path}")
            except Exception as e:
                self.log_message(f"⚠️ Could not save dry run: {e}")

            # Optionally open the folder (select file on Windows)
            try:
                if os.name == 'nt':
                    subprocess.run(["explorer", "/select,", report_path], check=False)
                elif sys.platform == 'darwin':
                    subprocess.run(["open", "-R", report_path], check=False)
                else:
                    folder = os.path.dirname(report_path) or "."
                    subprocess.run(["xdg-open", folder], check=False)
                self.log_message(f"📂 Opened folder containing: {report_path}")
            except Exception as e:
                self.log_message(f"⚠️ Could not open folder: {e}")

            # Ensure UI updates before quitting, then stop the application
            QApplication.processEvents()
            QApplication.quit()
            return

        # Step 7: Allow overwriting
        arcpy.env.overwriteOutput = True

        # Step 8: Add XY coordinates
        try:
            with arcpy.EnvManager(outputCoordinateSystem="GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]"):
                updated_features = arcpy.management.AddXY(feature_class)[0]
            self.log_message("✅ XY coordinates added")
        except Exception as e:
            self.log_message(f"⚠️ Failed to add XY: {e}")
            self.close()
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
            arcpy.management.MakeFeatureLayer(updated_features, layer_name, where_clause)

            # Build a safe folder/name for the TL
            safe_tl = "".join(c for c in tl if c.isalnum() or c in (' ', '_', '-')).rstrip()

            # Attempt to get Date_Fielded from the features in this TL group and use it in the filename.
            # Fall back to the current date if no valid Date_Fielded is found.
            date_str = datetime.now().strftime("%m_%d_%Y")  # default
            try:
                date_val = None
                with arcpy.da.SearchCursor(layer_name, ["Date_Fielded"]) as date_cursor:
                    for r in date_cursor:
                        if r and r[0]:
                            date_val = r[0]
                            break

                if date_val:
                    # If it's already a datetime, format directly
                    if isinstance(date_val, datetime):
                        date_str = date_val.strftime("%m_%d_%Y")
                    else:
                        # Try ISO parse first, then sanitize as a fallback
                        try:
                            parsed = datetime.fromisoformat(str(date_val))
                            date_str = parsed.strftime("%m_%d_%Y")
                        except Exception:
                            s = str(date_val)
                            # Replace common separators with underscores and remove extra whitespace
                            s = s.strip().replace('/', '_').replace('-', '_').replace(' ', '_')
                            # Keep only safe characters (alnum and underscore)
                            s = "".join(ch for ch in s if ch.isalnum() or ch == '_')
                            if s:
                                date_str = s
            except Exception as e:
                self.log_message(f"⚠️ Could not read Date_Fielded for TL {tl}: {e}")

            csv_output = os.path.join(output_folder, f"{safe_tl}_Fielding_{date_str}.csv")

            arcpy.conversion.ExportTable(layer_name, csv_output)
            self.log_message(f"✅ Exported table to: {csv_output}")
            arcpy.management.Delete(layer_name)

        # Step 10: Join fields
        try:
            arcpy.management.JoinField(
                in_data=attachment_table,
                in_field="REL_GLOBALID",
                join_table=feature_class,
                join_field="GlobalID",
                fields=["Structure_Number", "Scope_of_Work", "TL_Number", "Date_Fielded"]
            )
            self.log_message("✅ Fields joined successfully")
        except Exception as e:
            self.log_message(f"⚠️ Failed to join fields: {e}")

        # Step 11: Extract attachments
        try:
            with arcpy.da.SearchCursor(attachment_table, ['DATA', 'ATT_NAME', 'ATTACHMENTID', 'Structure_Number', 'TL_Number']) as cursor:
                for item in cursor:
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
                                base = base[:m.start(1)] + m.group(1).zfill(2)
                        att_part = base + ext
                    except Exception:
                        att_part = att_orig

                    # Combine structure number and attachment part (if present)
                    if struct_part and att_part:
                        att_name = f"{struct_part} {att_part}"
                    else:
                        att_name = att_part or struct_part or "attachment"

                    structure_num = struct_part if struct_part else "Unknown"
                    tl_number = str(item[4]) if item[4] else "Unknown"

                    tl_folder = os.path.join(output_folder, f"{tl_number}")
                    os.makedirs(tl_folder, exist_ok=True)

                    structure_folder = os.path.join(tl_folder, structure_num)
                    os.makedirs(structure_folder, exist_ok=True)

                    file_path = os.path.join(structure_folder, att_name)
                    try:
                        with open(file_path, 'wb') as f:
                            f.write(attachment.tobytes())
                        self.log_message(f"✅ Saved: {file_path}")
                    except Exception as e:
                        self.log_message(f"⚠️ Failed to save {att_name}: {e}")
        except Exception as e:
            self.log_message(f"⚠️ Failed to extract attachments: {e}")

        # Open output folder
        try:
            if os.name == 'nt':
                os.startfile(output_folder)
            elif sys.platform == 'darwin':
                subprocess.run(["open", output_folder], check=False)
            else:
                subprocess.run(["xdg-open", output_folder], check=False)
            self.log_message(f"📂 Opened output folder: {output_folder}")
        except Exception as e:
            self.log_message(f"⚠️ Could not open output folder: {e}")

        self.log_message("✅ Process completed successfully")
        self.close()  # close window when finished

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeodatabaseApp()
    window.resize(700, 500)
    window.show()
    sys.exit(app.exec())