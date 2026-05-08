import csv
import html
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

# Precompiled regex for stripping HTML tags (used in clean_html)
_tag_re = re.compile(r"<.*?>", flags=re.DOTALL)



def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r",
                       color=None):
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
        color       - Optional  : color code ('yellow', 'green', 'cyan', etc.)
    """
    # ANSI color codes
    colors = {
        'yellow': '\033[93m',
        'green': '\033[92m',
        'cyan': '\033[96m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }

    color_code = colors.get(color, 'green')
    reset_code = colors['reset'] if color else ''

    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{color_code}{prefix} |{bar}| {percent}% {suffix}{reset_code}', end=print_end)
    if iteration == total:
        print()


def format_duration(seconds):
    """Format seconds as minutes and seconds if >= 60, otherwise show seconds with two decimals."""
    if seconds >= 60:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins} minutes {secs:.2f} seconds"
    else:
        return f"{seconds:.2f} seconds"


def extract_kml_from_kmz(kmz_path, temp_dir, show_progress=True):
    """Extract KMZ and return path to first KML file."""
    with zipfile.ZipFile(kmz_path, "r") as z:
        members = z.namelist()
        # Fast extraction: extract all at once
        z.extractall(temp_dir)
        if show_progress:
            total_files = len(members)
            # Single progress update (fast)
            print_progress_bar(total_files, total_files, prefix='Extracting KMZ:', suffix='Complete', length=40,
                               color='yellow')

    for root, _, files in os.walk(temp_dir):
        for f in files:
            if f.lower().endswith(".kml"):
                return os.path.join(root, f)
    return None


def clean_html(text):
    """Remove HTML tags and decode HTML entities."""
    if not text:
        return ''
    text = html.unescape(text)
    # Use precompiled regex for speed
    text = _tag_re.sub('', text)
    return text.strip()


def parse_balloon_styles(kml_path, show_progress=True):
    """
    Stream-parse the KML file and extract all <Style id="..."> elements that contain
    a <BalloonStyle><text><![CDATA[...]]></text></BalloonStyle>. This uses ElementTree.iterparse
    to avoid loading the entire file into memory.
    Returns (styles_list, max_lines).
    """
    styles = []
    max_lines = 0

    try:
        # iterparse handles namespaces; use local name extraction
        for event, elem in ET.iterparse(kml_path, events=("end",)):
            local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if local == 'Style':
                style_id = elem.get('id')
                # Find BalloonStyle/text inside this Style
                cdata_text = None
                for child in elem:
                    if (child.tag.split('}')[-1] if '}' in child.tag else child.tag) == 'BalloonStyle':
                        for sub in child:
                            if (sub.tag.split('}')[-1] if '}' in sub.tag else sub.tag) == 'text':
                                # text may include CDATA/HTML
                                cdata_text = ''.join(sub.itertext()) or ''
                                break
                        break

                if cdata_text is not None:
                    # Extract <h3>
                    h3_match = re.search(r"<h3>(.*?)</h3>", cdata_text, flags=re.IGNORECASE | re.DOTALL)
                    h3_value = clean_html(h3_match.group(1)) if h3_match else None

                    # Extract all <td> values
                    td_raw = re.findall(r"<td>(.*?)</td>", cdata_text, flags=re.DOTALL | re.IGNORECASE)
                    lines = [clean_html(v) for v in td_raw if clean_html(v)]

                    max_lines = max(max_lines, len(lines))
                    styles.append({
                        "StyleID": style_id,
                        "H3": h3_value,
                        "Lines": lines
                    })

                # Free memory
                elem.clear()
    except ET.ParseError as e:
        # Fallback: if iterparse fails, return empty list; caller can handle
        print(f"Warning: XML parse error during streaming parse: {e}")

    if show_progress:
        print(f"📊 Analyzed KML content ({len(styles)} balloon styles found)...")

    return styles, max_lines


def write_csv(styles, max_lines, output_csv, show_progress=True):
    fieldnames = ["StyleID", "H3"] + [f"Line{i + 1}" for i in range(max_lines)]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        total_styles = len(styles)
        for i, s in enumerate(styles):
            if show_progress:
                print_progress_bar(i + 1, total_styles, prefix='Writing CSV:', suffix='Complete', length=40,
                                   color='yellow')

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
            print("\n📖 Processing file...")
        start_time = time.time()

        if kmz_or_kml.lower().endswith(".kmz"):
            if show_progress:
                print("📦 Extracting KMZ file...")
            kmz_start = time.time()
            kml_path = extract_kml_from_kmz(kmz_or_kml, temp_dir, show_progress=show_progress)
            if not kml_path:
                raise FileNotFoundError("No KML file found inside KMZ.")
            if show_timing:
                kmz_duration = time.time() - kmz_start
                print(f"KMZ extraction completed in {format_duration(kmz_duration)}.")
        else:
            kml_path = kmz_or_kml

        if show_progress:
            print("📖 Parsing KML file (streaming)...")
        analyze_start = time.time()
        styles, max_lines = parse_balloon_styles(kml_path, show_progress=show_progress)
        if show_timing:
            analyze_duration = time.time() - analyze_start
            print(f"KML content analysis completed in {format_duration(analyze_duration)}.")


        if mode == 'debug':
            print(f"\n[DEBUG] Found {len(styles)} balloon styles")
            print(f"[DEBUG] Maximum lines per style: {max_lines}")

        if show_progress:
            print("💾 Writing CSV...")
        write_start = time.time()
        write_csv(styles, max_lines, output_csv, show_progress=show_progress)
        if show_timing:
            write_duration = time.time() - write_start
            print(f"CSV writing completed in {format_duration(write_duration)}.")

        total_time = time.time() - start_time
        if show_timing:
            print(f"Total processing time: {format_duration(total_time)}\n")

        print("✅ Extraction complete!")
        print(f"💾 CSV saved to: {output_csv}")

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
    print("\n" + "=" * 50)
    print("KML Parser - Advanced Mode Selection")
    print("=" * 50)
    print("Select parsing mode:")
    print("  1 - Standard (with progress bars and timing)")
    print("  2 - Quick (fast mode, minimal output)")
    print("  3 - Debug (detailed output and diagnostics)")
    print("  4 - Exit")
    print("=" * 50)


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
    kmz_or_kml = input("\nPlease enter full path to your KMZ or KML file: ").strip().strip('"')
    output_csv = input("Please enter full path for output CSV (including .csv extension): ").strip().strip('"')

    try:
        process_kml(kmz_or_kml, output_csv, mode=mode, show_timing=(mode != 'quick'))
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
