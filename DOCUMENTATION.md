# Canvas2Tutor Technical Documentation

This document provides a technical overview of the `Canvas_Converter.py` script, detailing its class structure, key methods, and conversion logic.

## Class: `EnhancedCanvasConverter`

The core of the application, responsible for orchestrating the entire conversion process.

### Initialization

```python
def __init__(self, course_folder):
```
-   **Input**: `course_folder` (str) - Path to the root directory of the Canvas course export.
-   **Sets up**: Paths for input (manifest, resources) and output (`tutor_lms_output`).
-   **Initializes**: Statistics counter.

### Main Pipeline

The `generate_tutor_lms_structure` method drives the conversion through six stages:

1.  **Parse Manifest**: Reads `imsmanifest.xml` to build the course tree.
2.  **Discover Assignments**: Scans for folders containing assignment settings.
3.  **Generate Migration Guide**: Creates a summary text file.
4.  **Extract Content**: (Placeholder) Intended to process structured content.
5.  **Process Loose XML**: Finds and converts XML files not referenced in the manifest.
6.  **Save Outputs**: Writes the migration guide and structure JSON to disk.

### Key Methods

#### `parse_manifest(self)`
-   Parses the `imsmanifest.xml` file.
-   Extracts the course title and builds a resource map (identifier -> href/type).
-   Constructs a hierarchical dictionary representing the course modules and items.

#### `_process_loose_xml_files(self)`
-   Iterates through the entire course directory (excluding the output folder).
-   Identifies `.xml` files that are not system files (`imsmanifest.xml`, etc.).
-   Passes them to `_convert_loose_xml` for processing.

#### `_convert_loose_xml(self, xml_path, output_dir)`
-   Parses a single XML file.
-   Attempts to find content in `<body>`, `<text>`, or `<content>` tags.
-   If specific tags aren't found, falls back to converting the entire root to string.
-   Cleans the HTML content and saves it as an `.html` file.

#### `_clean_html(self, content)`
-   Unescapes HTML entities.
-   Fixes internal file references (replacing `$IMS-CC-FILEBASE$/` with `../web_resources/`).

#### `_save_html_file(self, filepath, title, content)`
-   Wraps the raw HTML content in a standard HTML5 boilerplate structure.
-   Saves the file with UTF-8 encoding.

## Data Structures

### Course Structure JSON
```json
{
  "title": "Course Title",
  "modules": [
    {
      "title": "Module Name",
      "items": [
        {
          "title": "Item Name",
          "content_file": "path/to/file.xml",
          "items": []
        }
      ]
    }
  ]
}
```

## Error Handling

-   The script includes basic error handling, particularly in `_convert_loose_xml`, where exceptions during file parsing or writing are caught, logged to the console, and tracked in the `missing_files` statistic.
