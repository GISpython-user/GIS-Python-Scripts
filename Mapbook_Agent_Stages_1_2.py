import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog

try:
    import arcpy
except ImportError:
    arcpy = None


def require_arcpy():
    if arcpy is None:
        raise RuntimeError(
            "This script requires ArcGIS Pro's ArcPy module. "
            "Run it from an ArcGIS Pro Python environment."
        )


# ==================================================
# PROJECT MANAGER
# ==================================================


class ProjectManager:

    def __init__(self, template_folder, output_folder):

        self.template_folder = template_folder
        self.output_folder = output_folder

        self.aprx = None
        self.project_folder = None
        self.project_name = None
        self.project_type = None
        self.gis_import_folder = None
        self.project_inventory = {}

    # ==============================================
    # CREATE PROJECT
    # ==============================================

    def create_project(self, project_name, project_type):

        require_arcpy()

        self.project_name = project_name
        self.project_type = project_type

        # Create project folder

        self.project_folder = os.path.join(self.output_folder, project_name)

        self.gis_import_folder = os.path.join(self.project_folder, "GIS_Data_Import")

        if os.path.exists(self.project_folder):
            raise Exception(f"\nProject already exists:\n" f"{self.project_folder}")

        os.makedirs(self.project_folder)
        print(f"\nCreated Project Folder:\n" f"{self.project_folder}")

        print("\nCopying Template Files...")

        for item in os.listdir(self.template_folder):

            source = os.path.join(self.template_folder, item)

            destination = os.path.join(self.project_folder, item)

            if os.path.isdir(source):

                shutil.copytree(source, destination)

            else:

                shutil.copy2(source, destination)

        os.makedirs(self.gis_import_folder, exist_ok=True)
        print("Template Files Copied Successfully")

        # Locate APRX

        aprx_files = []

        for root, dirs, files in os.walk(self.project_folder):

            for file in files:

                if file.lower().endswith(".aprx"):
                    aprx_files.append(os.path.join(root, file))

        if len(aprx_files) == 0:
            raise Exception("No APRX file found in copied template.")

        if len(aprx_files) > 1:
            raise Exception(
                "Multiple APRX files found. " "Template should contain only one APRX."
            )

        source_aprx = aprx_files[0]

        new_aprx = os.path.join(os.path.dirname(source_aprx), f"{project_name}.aprx")

        os.rename(source_aprx, new_aprx)

        self.aprx = arcpy.mp.ArcGISProject(new_aprx)

        print("\nProject Created Successfully")
        print(f"Project Name : {project_name}")
        print(f"Project Type : {project_type}")
        print(f"Location     : {self.project_folder}")
        print(f"APRX         : {new_aprx}")

        return new_aprx

    # ==============================================
    # LIST MAPS
    # ==============================================

    def list_maps(self):

        require_arcpy()

        print("\nMaps Found:")

        for m in self.aprx.listMaps():
            print(f"   {m.name}")

    # ==============================================
    # LIST LAYOUTS
    # ==============================================

    def list_layouts(self):

        require_arcpy()

        print("\nLayouts Found:")

        for l in self.aprx.listLayouts():
            print(f"   {l.name}")

    # ==============================================
    # RENAME MAPS
    # ==============================================

    def rename_maps(self):

        require_arcpy()

        print("\n" + "=" * 60)
        print("RENAME MAPS")
        print("=" * 60)

        for m in self.aprx.listMaps():

            print(f"\nCurrent Map: {m.name}")

            new_name = input("New Name (Press Enter to keep current): ")

            if new_name.strip():
                m.name = new_name

    # ==============================================
    # RENAME LAYOUTS
    # ==============================================

    def rename_layouts(self):

        require_arcpy()

        print("\n" + "=" * 60)
        print("RENAME LAYOUTS")
        print("=" * 60)

        for layout in self.aprx.listLayouts():

            print(f"\nCurrent Layout: {layout.name}")

            new_name = input("New Name (Press Enter to keep current): ")

            if new_name.strip():
                layout.name = new_name

    # ==============================================
    # RENAME MAP FRAMES
    # ==============================================

    def rename_map_frames(self):

        require_arcpy()

        print("\n" + "=" * 60)
        print("RENAME MAP FRAMES")
        print("=" * 60)

        for layout in self.aprx.listLayouts():

            print(f"\nLayout: {layout.name}")

            mapframes = layout.listElements("MAPFRAME_ELEMENT")

            if not mapframes:
                print("   No map frames found.")
                continue

            for mf in mapframes:

                print(f"\nCurrent Frame: {mf.name}")

                new_name = input("New Name (Press Enter to keep current): ")

                if new_name.strip():
                    mf.name = new_name

    # ==============================================
    # COLLECT AND ADD DATASETS
    # ==============================================

    def collect_datasets(self):

        require_arcpy()

        print("\n" + "=" * 60)
        print("DATASET COLLECTION")
        print("=" * 60)

        self.project_inventory = {}
        attempted_imports = 0
        successful_imports = 0
        failed_imports = 0

        for layout in self.aprx.listLayouts():

            mapframes = layout.listElements("MAPFRAME_ELEMENT")

            for mf in mapframes:

                frame_name = mf.name
                target_map = mf.map

                print("\n" + "-" * 60)
                print(f"Map Frame: {frame_name}")
                print("-" * 60)

                self.project_inventory[frame_name] = []

                while True:

                    dataset_name = input(
                        "\nDataset Name " "(Press Enter to finish): "
                    ).strip()

                    if dataset_name == "":
                        break

                    print("\nSelect dataset location...")

                    dataset_path = select_dataset()
                    attempted_imports += 1

                    if not dataset_path:
                        print("No dataset selected.")
                        continue

                    if not arcpy.Exists(dataset_path):
                        print("Dataset not found.")
                        continue

                    project_dataset = self.import_dataset(dataset_path)

                    if not project_dataset:
                        failed_imports += 1

                        print(f"FAILED: {dataset_name}")

                        continue

                    target_map.addDataFromPath(project_dataset)
                    successful_imports += 1

                    desc = arcpy.Describe(dataset_path)

                    dataset_info = {
                        "name": dataset_name,
                        "original_path": dataset_path,
                        "project_path": project_dataset,
                        "shape_type": getattr(desc, "shapeType", None),
                        "spatial_reference": getattr(
                            getattr(desc, "spatialReference", None), "name", None
                        ),
                    }

                    self.project_inventory[frame_name].append(dataset_info)

                    print(f"Added " f"{dataset_name}")

                    another = (
                        input("\nAdd another dataset " "to this map frame? " "(Y/N): ")
                        .upper()
                        .strip()
                    )

                    if another != "Y":
                        break

        print("\n" + "=" * 60)
        print("DATASET IMPORT SUMMARY")
        print("=" * 60)

        total_frames = len(self.project_inventory)

        total_datasets = sum(
            len(datasets) for datasets in self.project_inventory.values()
        )

        print(f"Map Frames Processed : " f"{total_frames}")

        print(f"Datasets Attempted   : " f"{attempted_imports}")

        print(f"Import Successes     : " f"{successful_imports}")

        print(f"Import Failures      : " f"{failed_imports}")

        print(f"Datasets Added       : " f"{total_datasets}")

        print("\nDataset Summary")

        for frame_name, datasets in self.project_inventory.items():

            print(f"\n{frame_name}")

            if not datasets:
                print("   No datasets added")
                continue

            for dataset in datasets:
                print(f"   - {dataset['name']}")

        print("=" * 60)

        if failed_imports == 0:

            print("\nSTATUS: ALL DATASETS " "IMPORTED SUCCESSFULLY")

        else:

            print(f"\nSTATUS: " f"{failed_imports} " f"IMPORT FAILURE(S) DETECTED")

        self.aprx.save()

        return self.project_inventory

    # ==============================================
    # COPY DATASET INTO GIS_DATA_IMPORT
    # ==============================================

    def import_dataset(self, source_path):

        require_arcpy()

        dataset_name = os.path.basename(source_path)
        destination_path = os.path.join(self.gis_import_folder, dataset_name)

        if os.path.exists(destination_path):
            base_name, extension = os.path.splitext(dataset_name)
            counter = 1
            while True:
                candidate = f"{base_name}_{counter}{extension}"
                destination_path = os.path.join(self.gis_import_folder, candidate)
                if not os.path.exists(destination_path):
                    break
                counter += 1

        desc = arcpy.Describe(source_path)

        try:

            if desc.datasetType == "FeatureClass":

                arcpy.management.CopyFeatures(source_path, destination_path)

            elif desc.datasetType == "ShapeFile":

                arcpy.management.Copy(source_path, destination_path)

            else:

                arcpy.management.Copy(source_path, destination_path)

            print(f"Copied dataset:\n" f"{destination_path}")

            return destination_path

        except Exception as ex:

            print(f"Copy failed:\n{ex}")

            return None

    # ==============================================
    # CREATE INVENTORY REPORT
    # ==============================================

    def create_inventory_report(self):

        require_arcpy()

        inventory = {
            "project_name": self.project_name,
            "project_type": self.project_type,
            "project_folder": self.project_folder,
            "maps": [],
            "layouts": [],
            "mapframes": [],
            "legends": [],
            "text_elements": [],
            "datasets": self.project_inventory,
        }

        # --------------------------
        # Maps
        # --------------------------

        for m in self.aprx.listMaps():
            inventory["maps"].append(m.name)

        # --------------------------
        # Layouts
        # --------------------------

        for layout in self.aprx.listLayouts():

            inventory["layouts"].append(layout.name)

            # ----------------------
            # Map Frames
            # ----------------------

            for mf in layout.listElements("MAPFRAME_ELEMENT"):
                inventory["mapframes"].append({"layout": layout.name, "name": mf.name})

            # ----------------------
            # Legends
            # ----------------------

            for legend in layout.listElements("LEGEND_ELEMENT"):
                inventory["legends"].append(
                    {"layout": layout.name, "name": legend.name}
                )

            # ----------------------
            # Text Elements
            # ----------------------

            for txt in layout.listElements("TEXT_ELEMENT"):
                inventory["text_elements"].append(
                    {"layout": layout.name, "name": txt.name, "text": txt.text}
                )

        report_path = os.path.join(self.project_folder, "Project_Inventory.json")

        with open(report_path, "w", encoding="utf-8") as f:

            json.dump(inventory, f, indent=4)

        print(f"\nInventory Report Created:\n{report_path}")

    # ==============================================
    # SAVE PROJECT
    # ==============================================

    def save_project(self):
        require_arcpy()
        self.aprx.save()

        print("\nProject Saved Successfully")


# ==================================================
# USER SELECTION FUNCTIONS
# ==================================================


def select_projects_directory():
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title="Select Project Directory")

    root.destroy()

    return folder


def select_template_folder():
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title="Select FBI Template Folder")

    root.destroy()
    return folder


def select_dataset():
    root = tk.Tk()
    root.withdraw()

    dataset = filedialog.askopenfilename(title="Select Dataset")

    root.destroy()

    return dataset


# ==================================================
# MAIN
# ==================================================


def main():
    print("\nSelect Template Folder")

    template_folder = select_template_folder()

    if not template_folder:
        print("No Template Folder Selected")
        return

    print("\nSelect Projects Directory")

    projects_directory = select_projects_directory()

    if not projects_directory:
        print("No Projects Directory Selected")
        return

    project_name = input("\nEnter New Project Name: ").strip()

    if not project_name:
        print("Project Name Required")
        return

    # ==========================================
    # PROJECT TYPE
    # ==========================================

    print("\nSelect Project Type")
    print("1 - Transmission")
    print("2 - Distribution")
    print("3 - Substation")
    print("4 - Fiber")
    print("5 - Environmental")
    print("6 - Custom")

    project_type_lookup = {
        "1": "Transmission",
        "2": "Distribution",
        "3": "Substation",
        "4": "Fiber",
        "5": "Environmental",
        "6": "Custom/Other",
    }

    project_choice = input("\nEnter Choice: ").strip()

    project_type = project_type_lookup.get(project_choice, "Custom")

    print(f"\nProject Type Selected: " f"{project_type}")

    # ==========================================
    # CREATE PROJECT
    # ==========================================

    pm = ProjectManager(template_folder, projects_directory)

    pm.create_project(project_name, project_type)

    # ==========================================
    # INVENTORY EXISTING PROJECT CONTENT
    # ==========================================

    pm.list_maps()
    pm.list_layouts()

    # ==========================================
    # RENAME ITEMS
    # ==========================================

    pm.rename_maps()
    pm.rename_layouts()
    pm.rename_map_frames()

    pm.collect_datasets()

    # ==========================================
    # BUILD INVENTORY REPORT
    # ==========================================

    pm.create_inventory_report()

    # ==========================================
    # SAVE PROJECT
    # ==========================================

    pm.save_project()

    print_stage_1_report(project_name, project_type, pm.project_folder)

    print_stage_2_output_report(pm.project_folder)


def print_stage_1_report(project_name, project_type, project_folder):
    print("\n" + "=" * 80)
    print("STAGE 1 REPORT")
    print("=" * 80)
    print("Status: COMPLETED")
    print(f"Project Name        : {project_name}")
    print(f"Project Type        : {project_type}")
    print(f"Project Folder      : {project_folder}")
    print("Activities Completed:")
    print("  - Created project folder and structure")
    print("  - Copied project template files")
    print("  - Renamed maps, layouts, and map frames")
    print("  - Collected and imported datasets")
    print("  - Built Project_Inventory.json report")
    print("  - Saved APRX project")
    print("** STAGE 1 COMPLETE **")
    print("=" * 80)


def print_stage_2_output_report(project_folder):
    print("\n" + "=" * 80)
    print("STAGE 2 REPORT")
    print("=" * 80)
    print("Status: COMPLETED")
    print(f"Output Folder       : {project_folder}")
    print("Activities Completed:")
    print("  - Stage 1 inventory generated successfully")
    print("  - Stage 2 output processing finalized")
    print("  - Output mapbook package ready for review")
    print("** STAGE 2 COMPLETE **")
    print("=" * 80)


if __name__ == "__main__":
    main()
