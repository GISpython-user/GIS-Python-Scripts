import json
import os
import tkinter as tk
from tkinter import filedialog

import arcpy


class Stage3MultiKMLLoader:

    def __init__(self):

        self.aprx = None
        self.inventory = None
        self.project_folder = None

        self.datasets_loaded = 0
        self.datasets_failed = 0

        self.kml_results = []

    # ==================================================
    # FOLDER SELECTION
    # ==================================================

    def select_project_folder(self):

        root = tk.Tk()
        root.withdraw()

        project_folder = filedialog.askdirectory(title="Select Project Folder")

        return project_folder

    # ==================================================
    # KML FILE PICKER
    # ==================================================

    def select_kml_files(self):

        root = tk.Tk()
        root.withdraw()

        return filedialog.askopenfilenames(
            title="Select KML/KMZ Files", filetypes=[("KML/KMZ Files", "*.kml *.kmz")]
        )

    # ==================================================
    # PROJECT
    # ==================================================

    def open_project(self):

        aprx_files = [
            f for f in os.listdir(self.project_folder) if f.lower().endswith(".aprx")
        ]

        if not aprx_files:
            raise Exception("No APRX found in project folder.")

        aprx_path = os.path.join(self.project_folder, aprx_files[0])

        print("\nOpening Project...")
        self.aprx = arcpy.mp.ArcGISProject(aprx_path)

        print(f"Opened: {aprx_path}")

    # ==================================================
    # INVENTORY
    # ==================================================

    def load_inventory(self):

        inventory_files = [
            f for f in os.listdir(self.project_folder) if f.lower().endswith(".json")
        ]

        if not inventory_files:
            raise Exception("No inventory file found.")

        inventory_path = os.path.join(self.project_folder, inventory_files[0])

        with open(inventory_path, "r") as f:
            self.inventory = json.load(f)

        print(f"\nInventory Loaded:\n{inventory_path}")

    # ==================================================
    # MAP SEARCH
    # ==================================================

    def get_map(self, map_name):

        for m in self.aprx.listMaps():

            if m.name == map_name:
                return m

        return None

    # ==================================================
    # LOAD STANDARD DATASETS
    # ==================================================

    def load_standard_datasets(self):

        print("\n================================")
        print("LOADING STANDARD DATASETS")
        print("================================")

        for map_name, datasets in self.inventory.items():

            target_map = self.get_map(map_name)

            if not target_map:

                print(f"Map Not Found: {map_name}")

                for _ in datasets:
                    self.datasets_failed += 1

                continue

            print(f"\nProcessing Map: {map_name}")

            for ds in datasets:

                try:

                    target_map.addDataFromPath(ds["path"])

                    self.datasets_loaded += 1

                    print(f"SUCCESS -> " f"{ds['name']}")

                except Exception as e:

                    self.datasets_failed += 1

                    print(f"FAILED -> " f"{ds['name']}")

                    print(str(e))

    # ==================================================
    # MAP SELECTION
    # ==================================================

    def choose_destination_map(self):

        maps = self.aprx.listMaps()

        if not maps:
            raise Exception("No maps found.")

        print("\nAvailable Maps")

        for i, m in enumerate(maps, start=1):
            print(f"{i}. {m.name}")

        selection = int(input("\nSelect Destination Map: "))

        return maps[selection - 1]

    # ==================================================
    # KML PROCESSING
    # ==================================================

    def process_kml_files(self):

        answer = input("\nProcess KML/KMZ files? (Y/N): ").upper()

        if answer != "Y":
            return

        kml_files = self.select_kml_files()

        if not kml_files:
            return

        output_folder = os.path.join(self.project_folder, "kml_data_conversion_output")

        os.makedirs(output_folder, exist_ok=True)

        for kml_file in kml_files:

            print("\n--------------------------------")
            print(f"Processing " f"{os.path.basename(kml_file)}")
            print("--------------------------------")

            result = {
                "file": os.path.basename(kml_file),
                "success": False,
                "map": "",
                "layers": 0,
                "message": "",
            }

            try:

                target_map = self.choose_destination_map()

                base_name = os.path.splitext(os.path.basename(kml_file))[0]

                existing_gdb = os.path.join(output_folder, f"{base_name}.gdb")

                if arcpy.Exists(existing_gdb):

                    choice = input(
                        f"\n{base_name}.gdb " f"already exists.\n" f"Overwrite? (Y/N): "
                    ).upper()

                    if choice != "Y":
                        result["message"] = "Skipped By User"

                        self.kml_results.append(result)

                        continue

                    arcpy.management.Delete(existing_gdb)

                print("\nRunning KML To Layer...")

                arcpy.conversion.KMLToLayer(kml_file, output_folder)

                gdb_path = os.path.join(output_folder, f"{base_name}.gdb")

                if not arcpy.Exists(gdb_path):
                    raise Exception("Output GDB not created.")

                added_layers = 0

                arcpy.env.workspace = gdb_path

                feature_classes = arcpy.ListFeatureClasses() or []

                for fc in feature_classes:
                    fc_path = os.path.join(gdb_path, fc)

                    target_map.addDataFromPath(fc_path)

                    added_layers += 1

                feature_datasets = arcpy.ListDatasets(feature_type="feature") or []

                for fd in feature_datasets:

                    fd_path = os.path.join(gdb_path, fd)

                    arcpy.env.workspace = fd_path

                    sub_fcs = arcpy.ListFeatureClasses() or []

                    for fc in sub_fcs:
                        fc_path = os.path.join(fd_path, fc)

                        target_map.addDataFromPath(fc_path)

                        added_layers += 1

                result["success"] = True
                result["map"] = target_map.name
                result["layers"] = added_layers
                result["message"] = "Success"

                print(f"SUCCESS - " f"{added_layers} layers added")

            except Exception as e:

                result["message"] = str(e)

                print(f"FAILED - {str(e)}")

            self.kml_results.append(result)

    # ==================================================
    # SAVE PROJECT
    # ==================================================

    def save_project(self):

        print("\nSaving Project...")

        self.aprx.save()

        print("Project Saved")

    # ==================================================
    # REPORT
    # ==================================================

    def report(self):

        print("\n")
        print("=" * 60)
        print("STAGE 3 COMPLETE")
        print("=" * 60)

        print("\nSTANDARD DATASETS")

        print(f"Loaded: " f"{self.datasets_loaded}")

        print(f"Failed: " f"{self.datasets_failed}")

        successful = 0
        failed = 0

        print("\nKML PROCESSING")

        for result in self.kml_results:

            print("\n----------------------")

            print(f"File: {result['file']}")

            print(f"Map: {result['map']}")

            print(f"Layers Added: " f"{result['layers']}")

            print(f"Message: " f"{result['message']}")

            if result["success"]:
                successful += 1
            else:
                failed += 1

        print("\n----------------------")

        print(f"Successful KMLs: " f"{successful}")

        print(f"Failed KMLs: " f"{failed}")

        print(f"Total KMLs: " f"{len(self.kml_results)}")

        print("\nProject Saved: YES")

        print("=" * 60)

    # ==================================================
    # RUN
    # ==================================================

    def run(self):

        self.project_folder = self.select_project_folder()

        if not self.project_folder:
            return

        self.open_project()

        self.load_inventory()

        self.load_standard_datasets()

        self.process_kml_files()

        self.save_project()

        self.report()


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":
    loader = Stage3MultiKMLLoader()

    loader.run()
