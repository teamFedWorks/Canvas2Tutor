# Testing Guide - Canvas to Tutor LMS Migration Pipeline \ NextGen LMS

## [QUICK START]

### Step 1: Install Dependencies

```bash
# Navigate to the converter directory
cd b:\UHUB\Converter

# Install required packages
pip install -r requirements.txt
```

### Step 2: Prepare Test Data

You have **two options**:

#### Option A: Use Your Own Canvas Export
1. Export a course from Canvas (Settings → Export Course Content)
2. Download and unzip the export
3. Note the directory path

#### Option B: Create a Minimal Test Structure
```bash
# Create a minimal test course
mkdir test_course
cd test_course

# Create imsmanifest.xml (minimal valid structure)
# See example below
```

### Step 3: Run the Converter

```bash
# Basic test
python Canvas_Converter.py ./test_course

# Or with your Canvas export
python Canvas_Converter.py "C:\path\to\your\canvas_export"
```

---

## [DETAILED STEPS]

### [1] Dependency Installation Test

```bash
pip install -r requirements.txt
```

**Expected Output:**
```
Successfully installed lxml-4.9.0 pydantic-2.0.0 beautifulsoup4-4.12.0 bleach-6.0.0 ...
```

**Verify Installation:**
```bash
python -c "import lxml; import pydantic; import bs4; print('[DONE] All dependencies installed')"
```

---

### [2] Create Minimal Test Course

Create this structure to test basic functionality:

```
test_course/
├── imsmanifest.xml
├── wiki_content/
│   └── page1.xml
└── web_resources/
    └── image.png
```

**imsmanifest.xml** (minimal):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="test_course" 
          xmlns="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1">
  <metadata>
    <schema>IMS Common Cartridge</schema>
    <schemaversion>1.1.0</schemaversion>
  </metadata>
  <organizations>
    <organization identifier="org1">
      <item identifier="module1">
        <title>Test Module</title>
        <item identifier="page1" identifierref="res_page1">
          <title>Test Page</title>
        </item>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="res_page1" type="webcontent" href="wiki_content/page1.xml">
      <file href="wiki_content/page1.xml"/>
    </resource>
  </resources>
</manifest>
```

**wiki_content/page1.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<page>
  <title>Welcome Page</title>
  <body>
    <h1>Welcome to the Test Course</h1>
    <p>This is a test page to verify the migration pipeline.</p>
  </body>
  <workflow_state>active</workflow_state>
</page>
```

---

### 3️⃣ Run Basic Test

```bash
python Canvas_Converter.py ./test_course
```

**Expected Output:**
```
================================================================================
CANVAS → TUTOR LMS MIGRATION PIPELINE \ NextGen LMS v2.0
================================================================================

[1/5] Validating Canvas export structure...
✓ Validation passed
  - Found 1 pages
  - Found 1 modules

[2/5] Parsing Canvas content...
  Processing orphaned XML/HTML files...
  Found 0 orphaned XML files
✓ Parsed course: Test Course
  - Modules: 1
  - Pages: 1
  - Assignments: 0
  - Quizzes: 0

[3/5] Transforming to Tutor LMS format...
✓ Transformed to Tutor LMS
  - Topics: 1
  - Lessons: 1
  - Quizzes: 0
  - Questions: 0

[4/5] Exporting to JSON...
✓ Exported to ./test_course/tutor_lms_output
  - Output size: 0.XX MB

[5/5] Generating migration reports...
✓ Reports generated

================================================================================
MIGRATION COMPLETE
================================================================================
Status: SUCCESS
Errors: 0
Warnings: 0
Execution time: X.XXs

Output directory: ./test_course/tutor_lms_output
  - tutor_course.json
  - migration_report.json
  - migration_report.html
  - IMPORT_INSTRUCTIONS.md
================================================================================
```

---

### 4️⃣ Verify Output

**Check Output Files:**
```bash
cd test_course/tutor_lms_output
dir  # or ls on Linux/Mac
```

**Should see:**
- ✅ `tutor_course.json`
- ✅ `migration_report.json`
- ✅ `migration_report.html`
- ✅ `IMPORT_INSTRUCTIONS.md`

**View Migration Report:**
```bash
# Open in browser
start migration_report.html  # Windows
# or
open migration_report.html   # Mac
# or
xdg-open migration_report.html  # Linux
```

**Inspect JSON Output:**
```bash
# View course structure
python -m json.tool tutor_course.json
```

---

### 5️⃣ Test XML Conversion (PowerPoint/Orphaned Files)

**Add orphaned XML file:**

Create `test_course/loose_content.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<document>
  <title>Supplemental Material</title>
  <content>
    <p>This is orphaned content that wasn't in the manifest.</p>
    <p>It should still be converted!</p>
  </content>
</document>
```

**Run converter again:**
```bash
python Canvas_Converter.py ./test_course
```

**Expected Output (additional):**
```
[2/5] Parsing Canvas content...
  Processing orphaned XML/HTML files...
  Found 1 orphaned XML files
  ✓ Converted orphaned XML: loose_content.xml
✓ Parsed course: Test Course
  - Pages: 2 (1 original + 1 orphaned)
```

---

## 🔍 Troubleshooting

### Error: "Module not found"
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Error: "imsmanifest.xml not found"
```
❌ Validation failed
Error: Required file not found: imsmanifest.xml
```
**Solution:** Ensure you're pointing to the correct directory containing `imsmanifest.xml`

### Error: "Failed to parse manifest"
**Solution:** Check that `imsmanifest.xml` is valid XML (use an XML validator)

### No Output Files Created
**Check:**
1. Do you have write permissions in the directory?
2. Check the console output for errors
3. Review `migration_report.html` for details

---

## ✅ Validation Checklist

After running the converter, verify:

- [ ] No critical errors in console output
- [ ] `tutor_course.json` exists and is valid JSON
- [ ] `migration_report.html` shows SUCCESS status
- [ ] All pages/quizzes/assignments counted correctly
- [ ] Orphaned XML files were detected and converted
- [ ] Asset paths rewritten correctly (check JSON for `assets/` paths)

---

## 🎯 Advanced Testing

### Test with Real Canvas Export

1. **Export from Canvas:**
   - Go to Canvas course → Settings → Export Course Content
   - Select "Common Cartridge" format
   - Download and unzip

2. **Run Converter:**
   ```bash
   python Canvas_Converter.py "C:\Downloads\canvas_export_123"
   ```

3. **Review Report:**
   - Check `migration_report.html` for warnings
   - Verify content counts match Canvas
   - Check for unsupported question types

### Test Error Handling

**Test with invalid manifest:**
```bash
# Create invalid XML
echo "invalid xml" > test_course/imsmanifest.xml
python Canvas_Converter.py ./test_course
```

**Expected:** Clear error message about XML parsing failure

---

## 📊 Performance Testing

For large courses:

```bash
# Time the conversion
python -m cProfile -o profile.stats Canvas_Converter.py ./large_course

# View stats
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

---

## 🐛 Debug Mode

If you encounter issues, add debug output:

```python
# Add to Canvas_Converter.py (line 1)
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📞 Getting Help

If tests fail:

1. **Check migration report:** `migration_report.html` has detailed error messages
2. **Check console output:** Look for specific error messages
3. **Verify dependencies:** Run `pip list` to see installed versions
4. **Check file structure:** Ensure Canvas export is properly unzipped

---

## 🎉 Success Criteria

Your test is successful if:

✅ Converter runs without critical errors  
✅ Output files are created  
✅ Migration report shows SUCCESS or SUCCESS_WITH_WARNINGS  
✅ JSON structure is valid  
✅ Content counts match expectations  
✅ Orphaned XML files are detected and converted
