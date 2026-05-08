# KML Parser Advanced

A powerful Python utility for extracting and parsing KML/KMZ files into structured CSV format. Designed to handle large geographic data files with multiple parsing modes and real-time progress tracking.

## Features

- ✅ **KMZ & KML Support** - Extract and parse both KMZ (compressed) and KML files
- ✅ **Flexible Parsing Modes** - Choose between Standard, Quick, and Debug modes
- ✅ **Progress Tracking** - Real-time progress bars with color-coded output
- ✅ **Performance Metrics** - Detailed timing information for each processing step
- ✅ **HTML Cleaning** - Automatically cleans HTML tags and decodes entities from extracted data
- ✅ **Balloon Style Extraction** - Extracts all BalloonStyle elements with H3 headings and line data
- ✅ **CSV Export** - Exports structured data to CSV with dynamic column generation
- ✅ **Smart Duration Formatting** - Automatically converts durations over 60 seconds to minutes and seconds

## Requirements

- Python 3.6+
- Standard library modules (no external dependencies):
  - `csv`
  - `html`
  - `os`
  - `re`
  - `shutil`
  - `sys`
  - `tempfile`
  - `time`
  - `zipfile`

## Installation

1. Clone or download the `KML_parser_advanced.py` file
2. No additional packages to install - uses Python standard library only

## Usage

### Basic Usage

Run the script and follow the interactive menu:

```bash
python KML_parser_advanced.py
Parsing Modes
1. Standard Mode (Recommended)
Includes progress bars for all operations
Shows timing information for each step
Best for most use cases
Command: Select option 1 from menu
2. Quick Mode
Fast processing with minimal output
Skips progress bars and timing details
Ideal for batch processing or automated workflows
Command: Select option 2 from menu
3. Debug Mode
Detailed output with diagnostics
Shows number of balloon styles found and maximum lines per style
Helpful for troubleshooting or analyzing file structure
Command: Select option 3 from menu
Input Requirements
When prompted, provide:
Full path to KML/KMZ file - Complete file path (quotes optional)
Example: C:\Data\maps\sample.kmz
Output CSV path - Full path with .csv extension
Example: C:\Output\extracted_data.csv
Example Workflow
$ python KML_parser_advanced.py

==================================================
KML Parser - Advanced Mode Selection
==================================================
Select parsing mode:
  1 - Standard (with progress bars and timing)
  2 - Quick (fast mode, minimal output)
  3 - Debug (detailed output and diagnostics)
  4 - Exit
==================================================

Enter your choice (1-4): 1

📖 Processing the file...
📦 Extracting the KMZ file...
Extracting KMZ: |██████████████████████████████████████| 100.0% Complete
KMZ extraction was completed in 2.45 seconds.
📖 Reading KML file...
Reading KML file: |██████████████████████████████████████| 100.0% Complete
KML file read in 1.23 seconds.
📊 Analyzing KML content...
Processing balloon styles: |██████████████████████████████████████| 100.0% Complete
KML content analysis completed in 0.87 seconds.
💾 Writing CSV...
Writing CSV: |██████████████████████████████████████| 100.0% Complete
CSV writing completed in 0.34 seconds.
Total processing time: 4.89 seconds.

✅ Extraction complete!
💾 CSV saved to: C:\Output\extracted_data.csv
How It Works
Processing Pipeline
File Extraction
If KMZ: Decompresses and extracts all files, locates first KML file
If KML: Uses file directly
File Reading
Reads KML file in chunks for memory efficiency
Displays progress for large files
Content Analysis
Uses regex to find all <Style id="..."><BalloonStyle> blocks
Extracts CDATA sections containing HTML content
Cleans HTML tags and decodes entities
CSV Export
Creates dynamic columns based on maximum lines found
Generates columns: StyleID, H3, Line1, Line2, etc.
Writes all data to CSV file with UTF-8 encoding
Auto-Open
Automatically opens the output folder on Windows
Output Format
CSV structure:
StyleID,H3,Line1,Line2,Line3,...
style_id_1,Heading Text,Value 1,Value 2,Value 3,...
style_id_2,Heading Text,Value A,Value B,Value C,...
Features in Detail
Progress Bars
Colored progress indicators show real-time status:
🟨 Yellow - File extraction and reading
🟩 Green - Parsing and CSV writing
Automatically completes (no manual intervention needed)
Smart Timing
Duration less than 60 seconds:
Displays as: 2.45 seconds
Duration 60+ seconds:
Automatically converts to: 1 minutes 30.45 seconds
HTML Cleaning
Automatically:
Decodes HTML entities (&nbsp; → space, &lt; → <, etc.)
Removes all HTML tags (<td>, <br>, etc.)
Trims whitespace
Troubleshooting
"No KML file was found inside the KMZ"
The KMZ file may be corrupted or doesn't contain a KML file
Check that KMZ file opens with a standard archive tool
"Invalid choice. Please try again."
Enter a number between 1-4 from the menu
Avoid entering extra characters
Large file performance
Use Quick Mode for faster processing
Progress bars add minimal overhead but can be disabled
File reading is optimized with chunking
Output CSV is empty
Check if the KML file contains <BalloonStyle> elements
Use Debug Mode to see how many styles were found
Verify the KML file structure is valid
Technical Details
Memory Efficiency
Processes large files in configurable chunks
Temporary directory cleaned up automatically after processing
No entire file kept in memory during reading phase
Error Handling
Graceful handling of missing files
UTF-8 encoding for international characters
Automatic directory creation for output path
Cross-Platform
Works on Windows, macOS, and Linux
File path handling is OS-agnostic
Uses Python's os.path for compatibility
Limitations
Extracts first KML file found in KMZ (if multiple exist)
BalloonStyle extraction via regex (not XML parsing)
Requires valid UTF-8 encoded KML/KMZ files
Performance Benchmarks
Example on standard hardware:
Operation
Time (1MB KML)
KMZ Extraction
~0.5-1.0s
File Reading
~0.2-0.5s
Content Analysis
~0.3-0.8s
CSV Writing
~0.1-0.3s
Total
~1.1-2.6s
Contributing
To improve this parser, consider:
Adding batch file processing
Supporting multiple output formats (JSON, XML)
Implementing XML parsing instead of regex
Adding command-line arguments
License
Free to use and modify for personal or commercial projects.
Support
For issues or questions:
Check the Troubleshooting section
Run in Debug Mode for detailed diagnostics
Verify your KML/KMZ file format is valid
