# XML to HTML Conversion - Examples

The Canvas to Tutor LMS migration pipeline \ NextGen LMS **automatically converts XML files to HTML**, including:

## ✅ Supported XML Types

### 1. **PowerPoint XML Exports**
Canvas exports PowerPoint slides as XML. The system extracts:
- Slide titles
- Slide content
- Notes
- Text from all elements

**Example XML Structure:**
```xml
<slide>
  <title>Introduction to Python</title>
  <content>
    <p>Python is a high-level programming language</p>
    <p>Key features include:</p>
    <ul>
      <li>Easy to learn</li>
      <li>Versatile</li>
    </ul>
  </content>
</slide>
```

**Converted to:** Tutor Lesson with clean HTML

---

### 2. **Canvas Page XML**
Standard Canvas wiki pages in XML format:
```xml
<page>
  <title>Week 1 Overview</title>
  <body>
    <h1>Welcome to Week 1</h1>
    <p>This week we'll cover...</p>
  </body>
</page>
```

**Converted to:** Tutor Lesson

---

### 3. **Generic XML Content**
Any XML file with text content:
```xml
<document>
  <heading>Course Syllabus</heading>
  <text>
    Course objectives...
  </text>
</document>
```

**Converted to:** Tutor Lesson with extracted text

---

## 🔄 How It Works

### Automatic Processing

The pipeline automatically:

1. **Detects Orphaned XML Files**
   - Scans entire course directory
   - Finds XML files not referenced in `imsmanifest.xml`
   - Includes PowerPoint exports, loose content files

2. **Extracts Content**
   - Tries multiple common XML elements: `<body>`, `<content>`, `<text>`, `<slide-content>`, `<p>`
   - Falls back to extracting all text if structured elements not found
   - Preserves HTML formatting

3. **Creates Tutor Lessons**
   - Converts each XML file to a Tutor Lesson
   - Uses filename as title (if no title element found)
   - Cleans and sanitizes HTML

4. **Reports Results**
   - Lists all converted files in migration report
   - Flags any parsing errors
   - Shows count of orphaned content recovered

---

## 📊 Example Output

When you run the converter:

```
[2/5] Parsing Canvas content...
  Processing orphaned XML/HTML files...
  Found 15 orphaned XML files
  ✓ Converted orphaned XML: lecture_slides_week1.xml
  ✓ Converted orphaned XML: supplemental_reading.xml
  ✓ Converted orphaned XML: powerpoint_export_123.xml
  ...
✓ Parsed course: Introduction to Computer Science
  - Pages: 45 (including 15 from orphaned XML)
```

---

## 🎯 Specific Features for PowerPoint XML

The `OrphanedContentHandler` specifically looks for:

- **Slide titles**: `<title>`, `<slide-title>`, `<heading>`, `<h1>`
- **Slide content**: `<content>`, `<slide-content>`, `<body>`, `<text>`
- **Notes**: `<notes>`, `<description>`
- **Paragraphs**: `<p>` elements

All content is combined into a single HTML lesson.

---

## 💡 Usage

**No special configuration needed!** Just run:

```bash
python Canvas_Converter.py ./your-canvas-export
```

The system will automatically:
1. Parse all referenced content
2. Find orphaned XML/HTML files
3. Convert them to Tutor Lessons
4. Include them in the output

---

## 📝 Migration Report

Check `migration_report.html` to see:
- How many orphaned files were found
- Which files were successfully converted
- Any files that failed to parse

---

## ⚙️ Advanced: Custom XML Structures

If you have custom XML structures, the handler will:
1. Try common element names first
2. Fall back to extracting all text content
3. Wrap text in HTML paragraphs

For very specific XML structures, you can extend `OrphanedContentHandler` in:
`src/parsers/orphaned_content_handler.py`
