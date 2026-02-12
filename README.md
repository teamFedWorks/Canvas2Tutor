# Canvas2Tutor - Production Migration Pipeline

A **production-grade** Canvas LMS to Tutor LMS migration pipeline with zero data loss, full schema compliance, and deterministic output.

## 🚀 Features

### Core Capabilities
- ✅ **5-Stage Pipeline**: Validation → Parsing → Resolution → Transformation → Export
- ✅ **Zero Data Loss**: Every file tracked, orphaned content recovered, all errors logged
- ✅ **Schema-Aware Parsing**: Dedicated parsers for pages, assignments, quizzes, questions
- ✅ **QTI-Compliant**: Proper handling of all Canvas question types
- ✅ **Type-Safe**: Full Python type hints with dataclass models
- ✅ **Comprehensive Reporting**: JSON + HTML migration reports

### Content Support
- **Pages** → Tutor Lessons
- **Assignments** → Tutor Assignments  
- **Quizzes** → Tutor Quizzes
- **Questions** (20+ types) → Tutor Questions
- **Modules** → Tutor Topics
- **Assets** (images, videos, files)

## 📋 Prerequisites

- Python 3.9 or higher
- Canvas course export (IMS-CC format)

## 🛠️ Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## 📖 Usage

### Basic Usage

```bash
python Canvas_Converter.py <course_directory>
```

### With Custom Output Directory

```bash
python Canvas_Converter.py <course_directory> <output_directory>
```

### Example

```bash
python Canvas_Converter.py ./cs-1143
```

## 📂 Output Structure

```
tutor_lms_output/
├── tutor_course.json          # Complete course structure
├── migration_report.json      # Machine-readable report
├── migration_report.html      # Human-readable report
└── IMPORT_INSTRUCTIONS.md     # Import guide
```

## 🏗️ Architecture

### Pipeline Stages

1. **Validation & Inventory**
   - Validates IMS-CC structure
   - Builds content inventory
   - Detects orphaned files

2. **Semantic Parsing**
   - Parses `imsmanifest.xml` (single source of truth)
   - Extracts pages, assignments, quizzes, questions
   - QTI-compliant question parsing

3. **Content Resolution**
   - Resolves asset paths
   - Rewrites internal links
   - Handles orphaned content

4. **Tutor LMS Transformation**
   - Maps Canvas entities to Tutor entities
   - Preserves hierarchy and ordering
   - Converts question types

5. **Export & Verification**
   - Exports to JSON format
   - Verifies referential integrity
   - Generates migration reports

### Data Models

- **Canvas Models**: `CanvasCourse`, `CanvasModule`, `CanvasPage`, `CanvasAssignment`, `CanvasQuiz`, `CanvasQuestion`
- **Tutor Models**: `TutorCourse`, `TutorTopic`, `TutorLesson`, `TutorQuiz`, `TutorQuestion`, `TutorAssignment`
- **Reports**: `ValidationReport`, `ParseReport`, `TransformationReport`, `VerificationReport`, `MigrationReport`

## 📊 Question Type Mapping

| Canvas Question Type | Tutor LMS Type | Notes |
|---------------------|----------------|-------|
| Multiple Choice | Multiple Choice | Direct mapping |
| True/False | True/False | Direct mapping |
| Essay | Open-ended | Direct mapping |
| Short Answer | Short Answer | Direct mapping |
| Fill in Blank | Fill in Blank | Direct mapping |
| Matching | Matching | Direct mapping |
| Numerical | Short Answer | Fallback |
| Calculated | Open-ended | Fallback - requires review |
| File Upload | Open-ended | Fallback - requires review |
| Formula | Open-ended | Fallback - requires review |

## 🔍 Migration Report

The migration generates comprehensive reports:

### JSON Report
- Machine-readable format
- Complete error log
- Content counts
- Question type mappings

### HTML Report
- Human-readable format
- Visual summary
- Color-coded errors/warnings
- Content comparison table

## ⚠️ Important Notes

- **Unsupported Features**: Some advanced Canvas question types (formula, calculated) are converted to essay questions with metadata flags
- **Manual Review**: Check the migration report for warnings and items requiring manual review
- **Asset Paths**: Asset references are rewritten to `assets/` directory
- **Orphaned Content**: Files not in manifest are placed in "Recovered Content" module

## 🧪 Testing

```bash
# Run with a sample Canvas export
python Canvas_Converter.py ./sample_course

# Check the output
cat tutor_lms_output/migration_report.html
```

## 📚 Documentation

- **Architecture**: See `architecture.md` in artifacts
- **Implementation Plan**: See `implementation_plan.md` in artifacts
- **API Documentation**: See inline docstrings

## 🤝 Contributing

This is a production-grade migration tool. Contributions should:
- Maintain type safety
- Include comprehensive error handling
- Update migration reports
- Add tests for new features

## 📄 License

MIT License

## 🆘 Support

For issues or questions:
1. Check the migration report for detailed error messages
2. Review `IMPORT_INSTRUCTIONS.md` in output directory
3. Consult the architecture documentation

---

**Version**: 2.0.0  
**Status**: Production-Ready  
**Quality Bar**: Zero silent data loss, comprehensive error reporting, deterministic output
