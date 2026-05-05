import csv
import html
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        print_end   - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()


def extract_kml_from_kmz(kmz_path, temp_dir):
    """Extract KMZ and return path to first KML file."""
    zip_path = os.path.join(temp_dir, "temp.zip")
    shutil.copy(kmz_path, zip_path)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp_dir)

    for root, _, files in os.walk(temp_dir):
        for f in files:
            if f.lower().endswith(".kml"):
                return os.path.join(root, f)
    return None


def clean_html(text):
    """Remove HTML tags and decode HTML entities."""
    text = html.unescape(text)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()


def parse_balloon_styles(kml_text, show_progress=True):
    """
    Extract all <Style id="..."><BalloonStyle>...</BalloonStyle></Style>
    and return list of dicts with StyleID, H3, Lines.
    """
    styles = []

    # Find all Style blocks with BalloonStyle CDATA
    style_blocks = re.findall(
        r'<Style\s+id\s*=\s*"([^"]+)".*?<BalloonStyle>.*?<text>\s*<!\[CDATA\[(.*?)\]\]>\s*</text>',
        kml_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    max_lines = 0
    total_styles = len(style_blocks)

    for i, (style_id, cdata) in enumerate(style_blocks):
        if show_progress and (i + 1) % 10 == 0 or i + 1 == total_styles:
            print_progress_bar(i + 1, total_styles, prefix='Parsing balloon styles:', suffix='Complete', length=40)

        # Extract <h3>
        h3_match = re.search(r"<h3>(.*?)</h3>", cdata, flags=re.IGNORECASE | re.DOTALL)
        h3_value = clean_html(h3_match.group(1)) if h3_match else None

        # Extract all <td> values
        td_raw = re.findall(r"<td>(.*?)</td>", cdata, flags=re.DOTALL | re.IGNORECASE)
        lines = [clean_html(v) for v in td_raw if clean_html(v)]

        max_lines = max(max_lines, len(lines))

        styles.append({
            "StyleID": style_id,
            "H3": h3_value,
            "Lines": lines
        })

    return styles, max_lines


def write_csv(styles, max_lines, output_csv, show_progress=True):
    fieldnames = ["StyleID", "H3"] + [f"Line{i + 1}" for i in range(max_lines)]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        total_styles = len(styles)
        for i, s in enumerate(styles):
            if show_progress and ((i + 1) % 10 == 0 or i + 1 == total_styles):
                print_progress_bar(i + 1, total_styles, prefix='Writing CSV:', suffix='Complete', length=40)

            row = {
                "StyleID": s["StyleID"],
                "H3": s["H3"],
            }
            for j, val in enumerate(s["Lines"]):
                row[f"Line{j + 1}"] = val
            writer.writerow(row)


def process_kml(kmz_or_kml, output_csv, mode='standard', show_timing=True):
    """
    Main processing function
    mode options: 'standard', 'quick', 'debug'
    """
    show_progress = mode != 'quick'

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_csv)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    temp_dir = tempfile.mkdtemp()
    try:
        if mode in ['standard', 'debug']:
            print("\nProcessing file...")
        start_time = time.time()

        if kmz_or_kml.lower().endswith(".kmz"):
            if show_progress:
                print("Extracting KMZ file...")
            kmz_start = time.time()
            kml_path = extract_kml_from_kmz(kmz_or_kml, temp_dir)
            if not kml_path:
                raise FileNotFoundError("No KML file found inside KMZ.")
            if show_timing:
                kmz_duration = time.time() - kmz_start
                print(f"KMZ extraction completed in {kmz_duration:.2f} seconds.")
        else:
            kml_path = kmz_or_kml

        if show_progress:
            print("Reading KML file...")
        read_start = time.time()
        with open(kml_path, "r", encoding="utf-8") as f:
            kml_text = f.read()
        if show_timing:
            read_duration = time.time() - read_start
            print(f"KML file read in {read_duration:.2f} seconds.")

        if show_progress:
            print("Analyzing KML content...")
        analyze_start = time.time()
        styles, max_lines = parse_balloon_styles(kml_text, show_progress=show_progress)
        if show_timing:
            analyze_duration = time.time() - analyze_start
            print(f"KML content analysis completed in {analyze_duration:.2f} seconds.")

        if mode == 'debug':
            print(f"\n[DEBUG] Found {len(styles)} balloon styles")
            print(f"[DEBUG] Maximum lines per style: {max_lines}")

        write_start = time.time()
        write_csv(styles, max_lines, output_csv, show_progress=show_progress)
        if show_timing:
            write_duration = time.time() - write_start
            print(f"CSV writing completed in {write_duration:.2f} seconds.")

        total_time = time.time() - start_time
        if show_timing:
            print(f"Total processing time: {total_time:.2f} seconds.\n")

        print("✓ Extraction complete!")
        print(f"✓ CSV saved to: {output_csv}")

        # Open the output folder
        output_dir = os.path.dirname(output_csv)
        if output_dir:
            os.startfile(output_dir)
        else:
            os.startfile(os.getcwd())

    finally:
        shutil.rmtree(temp_dir)


def display_menu():
    """Display mode selection menu"""
    print("\n" + "="*50)
    print("KML Parser - Advanced Mode Selection")
    print("="*50)
    print("Select parsing mode:")
    print("  1 - Standard (with progress bars and timing)")
    print("  2 - Quick (fast mode, minimal output)")
    print("  3 - Debug (detailed output and diagnostics)")
    print("  4 - Exit")
    print("="*50)


def main():
    display_menu()
    mode_choice = input("\nEnter your choice (1-4): ").strip()

    mode_map = {
        '1': 'standard',
        '2': 'quick',
        '3': 'debug'
    }

    if mode_choice == '4':
        print("Exiting...")
        return

    if mode_choice not in mode_map:
        print("Invalid choice. Please try again.")
        return main()

    mode = mode_map[mode_choice]
    kmz_or_kml = input("\nEnter full path to your KMZ or KML file: ").strip().strip('"')
    output_csv = input("Enter full path for output CSV (including .csv): ").strip().strip('"')

    try:
        process_kml(kmz_or_kml, output_csv, mode=mode, show_timing=(mode != 'quick'))
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()