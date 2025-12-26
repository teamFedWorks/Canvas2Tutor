# Canvas2Tutor

A robust Python tool designed to convert Canvas course exports into a format compatible with Tutor LMS. This utility ensures a smooth migration of course content, including lessons, assignments, and quizzes, while preserving the original structure and data integrity.

## 🚀 Features

- **Comprehensive Conversion**: Handles Lessons, Quizzes, Assignments, and loose XML content.
- **Structure Preservation**: Parses `imsmanifest.xml` to maintain the original module and item hierarchy.
- **Content Cleaning**: Automatically cleans and formats HTML content, fixing broken links and unescaping characters.
- **Loose XML Recovery**: Scans for and converts XML files found outside the standard structure, ensuring no content is left behind.
- **Detailed Reporting**: Generates a migration guide, course structure JSON, and provides execution statistics.

## 📋 Prerequisites

- Python 3.6 or higher

## 🛠️ Usage

1.  **Prepare your Canvas Export**: Ensure you have the unzipped folder of your Canvas course export.
2.  **Run the Script**:
    ```bash
    python Canvas_Converter.py [path_to_course_folder]
    ```
    If no path is provided, it defaults to looking for a folder named `cs-2000`.

    **Example:**
    ```bash
    python Canvas_Converter.py "C:\Downloads\MyCanvasCourse"
    ```

## 📂 Output

The script creates a `tutor_lms_output` directory within the source course folder containing:

-   `lessons/`: Converted HTML lesson files.
-   `migration_guide.txt`: A text file summarizing the migration process.
-   `course_structure.json`: A JSON representation of the parsed course structure.

## 📊 Statistics

At the end of the execution, the script provides a summary of:
-   HTML and XML files processed
-   Quizzes and Assignments found
-   Loose XML files converted
-   Total lessons generated
-   Missing files encountered

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
