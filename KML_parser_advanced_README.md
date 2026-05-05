# KML Parser Advanced

A powerful Python script for extracting balloon style data from KML/KMZ files with multiple processing modes, progress tracking, and comprehensive error handling.

## Features

- **Multiple Processing Modes**: Standard, Quick, and Debug modes for different use cases
- **Progress Tracking**: Real-time progress bars and timing information
- **KMZ Support**: Automatic extraction of KML files from KMZ archives
- **HTML Cleaning**: Intelligent removal of HTML tags and entity decoding
- **Dynamic CSV Generation**: Automatically creates columns based on data structure
- **Auto Folder Creation**: Creates output directories if they don't exist
- **Auto Folder Opening**: Opens the output folder in Windows Explorer after completion
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Performance Monitoring**: Detailed timing information for each processing step

## Requirements

- Python 3.6+
- Standard library modules (no external dependencies)

## Installation

1. Download `KML_parser_advanced.py`
2. Ensure Python 3.6+ is installed on your system
3. Run the script directly: `python KML_parser_advanced.py`

## Usage

### Interactive Mode Selection

When you run the script, you'll see a menu:

```
==================================================
KML Parser - Advanced Mode Selection
==================================================
Select parsing mode:
  1 - Standard (with progress bars and timing)
  2 - Quick (fast mode, minimal output)
  3 - Debug (detailed output and diagnostics)
  4 - Exit
==================================================
```

### Processing Modes

#### 1. Standard Mode
- Full progress bars for parsing and CSV writing
- Detailed timing information for each step
- Comprehensive status messages
- Best for understanding processing progress

#### 2. Quick Mode
- Minimal output for fast processing
- No progress bars or timing information
- Ideal for batch processing or automation

#### 3. Debug Mode
- All standard mode features plus:
- Diagnostic information about found styles
- Detailed parsing statistics
- Helpful for troubleshooting parsing issues

### Input/Output

**Input**: Full path to KML or KMZ file
**Output**: CSV file with extracted balloon style data

## Output Format

The CSV file contains the following columns:

- **StyleID**: The unique identifier of the balloon style
- **H3**: The header text from the balloon (if present)
- **Line1, Line2, ...**: All table data extracted from the balloon content

### Example CSV Output

```csv
StyleID,H3,Line1,Line2,Line3
style1,Location Info,Latitude: 40.7128,Longitude: -74.0060,Elevation: 10m
style2,Weather Data,Temperature: 22°C,Humidity: 65%,Wind: 5 km/h
```

## How It Works

1. **File Processing**: Reads KML content (extracts from KMZ if needed)
2. **Style Extraction**: Finds all `<Style>` blocks with `<BalloonStyle>` content
3. **Data Parsing**: Extracts H3 headers and all table data (`<td>` elements)
4. **HTML Cleaning**: Removes HTML tags and decodes entities
5. **CSV Generation**: Creates dynamic columns based on maximum data found
6. **Output**: Saves to CSV and opens containing folder

## Examples

### Basic Usage

```bash
python KML_parser_advanced.py
# Select mode 1 (Standard)
# Enter: C:\path\to\your\file.kml
# Enter: C:\path\to\output\data.csv
```

### Command Line Integration

The script can be integrated into batch files or automated workflows:

```batch
@echo off
python KML_parser_advanced.py
```

### Processing Multiple Files

For batch processing, you can create a wrapper script:

```python
import subprocess
import os

files_to_process = [
    r"C:\data\file1.kmz",
    r"C:\data\file2.kml",
    r"C:\data\file3.kmz"
]

for input_file in files_to_process:
    output_file = os.path.splitext(input_file)[0] + "_parsed.csv"
    # Note: This would require modifying the script to accept command line args
    # subprocess.run(["python", "KML_parser_advanced.py", input_file, output_file])
```

## Troubleshooting

### Common Issues

#### "No KML file found inside KMZ"
- **Cause**: The KMZ file may be corrupted or contain no KML files
- **Solution**: Verify the KMZ file is valid and contains KML content

#### "Only two columns returned with no data"
- **Cause**: The KML file may have a different balloon style structure
- **Solution**: Use Debug mode to see what data is being found, then adjust parsing logic if needed

#### "Permission denied" when creating output folder
- **Cause**: Insufficient permissions to create directories
- **Solution**: Run as administrator or choose a different output location

#### "File not found" error
- **Cause**: Incorrect file path or file doesn't exist
- **Solution**: Verify the file path and ensure the file exists

### Debug Mode Tips

When using Debug mode, pay attention to:
- Number of balloon styles found
- Maximum lines per style
- Any error messages during parsing

### Performance Considerations

- **Large Files**: Use Quick mode for faster processing of large KML files
- **Many Styles**: Progress bars update every 10 styles to avoid performance impact
- **Memory Usage**: Files are processed in memory, ensure sufficient RAM for very large files

## File Structure

```
KML_parser_advanced.py
├── Functions:
│   ├── print_progress_bar()      # Progress bar display
│   ├── extract_kml_from_kmz()    # KMZ extraction
│   ├── clean_html()              # HTML cleaning
│   ├── parse_balloon_styles()    # Main parsing logic
│   ├── write_csv()               # CSV output
│   ├── process_kml()             # Main processing
│   ├── display_menu()            # Menu display
│   └── main()                    # Entry point
```

## Version History

- **v1.0**: Initial release with basic KML parsing
- **v2.0**: Added advanced modes, progress tracking, and menu system

## License

This script is provided as-is for educational and practical use. Modify and distribute as needed.

## Support

For issues or feature requests, please check the troubleshooting section or examine the debug output for clues about parsing problems.