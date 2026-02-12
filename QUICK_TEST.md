# 🧪 Quick Testing Instructions

## ⚡ Fastest Way to Test (3 Steps)

### Step 1: Install Dependencies (One-Time Setup)

Open PowerShell/Command Prompt and run:

```powershell
cd b:\UHUB\Converter
pip install lxml pydantic beautifulsoup4 bleach tqdm
```

**Expected:** "Successfully installed..." messages

---

### Step 2: Verify Setup

```powershell
python test_setup.py
```

**Expected Output:**
```
✓ src/models
✓ src/config
✓ src/utils
...
✓ ALL TESTS PASSED - System is ready!
```

---

### Step 3: Test with Your Canvas Export

**Option A: If you have a Canvas export**
```powershell
python Canvas_Converter.py "C:\path\to\your\canvas_export"
```

**Option B: Create a minimal test**

1. Create folder: `test_course`
2. Inside it, create `imsmanifest.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="test" xmlns="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1">
  <organizations>
    <organization identifier="org1">
      <item identifier="m1"><title>Test Module</title></item>
    </organization>
  </organizations>
  <resources></resources>
</manifest>
```

3. Run:
```powershell
python Canvas_Converter.py ./test_course
```

**Expected Output:**
```
================================================================================
CANVAS → TUTOR LMS MIGRATION PIPELINE v2.0
================================================================================

[1/5] Validating Canvas export structure...
✓ Validation passed

[2/5] Parsing Canvas content...
✓ Parsed course

[3/5] Transforming to Tutor LMS format...
✓ Transformed to Tutor LMS

[4/5] Exporting to JSON...
✓ Exported to ./test_course/tutor_lms_output

[5/5] Generating migration reports...
✓ Reports generated

================================================================================
MIGRATION COMPLETE
================================================================================
Status: SUCCESS
```

---

## 📁 Check Output

After running, check `test_course/tutor_lms_output/`:

- ✅ `tutor_course.json` - Course structure
- ✅ `migration_report.html` - Open this in browser!
- ✅ `migration_report.json` - Machine-readable report
- ✅ `IMPORT_INSTRUCTIONS.md` - Import guide

---

## 🎯 Test XML Conversion

Add a loose XML file to test orphaned content handling:

**Create `test_course/slides.xml`:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<presentation>
  <title>Lecture Slides</title>
  <content>
    <p>This is a PowerPoint export or loose content.</p>
    <p>It should be automatically converted!</p>
  </content>
</presentation>
```

**Run again:**
```powershell
python Canvas_Converter.py ./test_course
```

**Look for:**
```
[2/5] Parsing Canvas content...
  Processing orphaned XML/HTML files...
  Found 1 orphaned XML files
  ✓ Converted orphaned XML: slides.xml
```

---

## ✅ Success Indicators

You'll know it's working if:

1. ✅ No error messages in console
2. ✅ "MIGRATION COMPLETE" with "Status: SUCCESS"
3. ✅ Output files created in `tutor_lms_output/`
4. ✅ `migration_report.html` shows green SUCCESS badge
5. ✅ `tutor_course.json` contains your course structure

---

## 🐛 Troubleshooting

**"Module not found" errors:**
```powershell
pip install lxml pydantic beautifulsoup4 bleach tqdm --upgrade
```

**"imsmanifest.xml not found":**
- Make sure you're pointing to the directory containing `imsmanifest.xml`
- Check the path is correct

**"Permission denied":**
- Run PowerShell as Administrator
- Or use a different output directory

---

## 📞 Need Help?

1. Check `migration_report.html` for detailed errors
2. Look at console output for specific error messages
3. Verify dependencies: `pip list | findstr "lxml pydantic beautifulsoup4"`

---

## 🎉 Ready to Use!

Once tests pass, you can migrate real Canvas courses:

```powershell
python Canvas_Converter.py "C:\Downloads\my_canvas_course_export"
```

The system will:
- ✅ Validate the export
- ✅ Parse all content (pages, quizzes, assignments)
- ✅ Convert orphaned XML/HTML files
- ✅ Transform to Tutor LMS format
- ✅ Generate comprehensive reports
- ✅ Create import-ready JSON

**Output:** `tutor_course.json` ready for Tutor LMS import!
