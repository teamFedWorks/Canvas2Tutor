# Canvas2Tutor - Production Migration Pipeline \ NextGen LMS

A **production-grade** Canvas LMS to Tutor LMS migration pipeline \ NextGen LMS with zero data loss, full schema compliance, and deterministic output.

## [FEATURES]

### Core Capabilities
- [PASS] **5-Stage Pipeline**: Validation → Parsing → Resolution → Transformation → Export
- [PASS] **Zero Data Loss**: Every file tracked, orphaned content recovered, all errors logged
- [PASS] **Schema-Aware Parsing**: Dedicated parsers for pages, assignments, quizzes, questions
- [PASS] **QTI-Compliant**: Proper handling of all Canvas question types
- [PASS] **Type-Safe**: Full Python type hints with dataclass models
- [PASS] **Comprehensive Reporting**: JSON + HTML migration reports

### Content Support
- **Pages** → Tutor Lessons
- **Assignments** → Tutor Assignments  
- **Quizzes** → Tutor Quizzes
- **Questions** (20+ types) → Tutor Questions
- **Modules** → Tutor Topics
- **Assets** (images, videos, files)

## [PREREQUISITES]

- Python 3.9 or higher
- Canvas course export (IMS-CC format)

## [INSTALLATION]

```bash
# Install dependencies
pip install -r requirements.txt
```

## [USAGE]

### Basic Usage (Convert Only)

```bash
python Canvas_Converter.py <course_directory>
```

### With Custom Output Directory

```bash
python Canvas_Converter.py <course_directory> <output_directory>
```

### One-Command: Convert + Upload to MongoDB

```bash
# Convert and upload in one command
python Canvas_Converter.py <course_directory> --upload

# With custom environment file
python Canvas_Converter.py <course_directory> --upload --env-file .env.production
```

### Examples

```bash
# Just convert to JSON
python Canvas_Converter.py ./cs-1143

# Convert and upload to MongoDB (one command!)
python Canvas_Converter.py ./cs-1143 --upload

# Convert with custom output, then upload
python Canvas_Converter.py ./cs-1143 ./my-output --upload
```

### Command-Line Options

```bash
python Canvas_Converter.py --help
```

**Positional Arguments:**
- `course_directory` - Path to Canvas course export directory (required)
- `output_directory` - Optional output directory (default: course_dir/tutor_lms_output)

**Optional Flags:**
- `--upload` - Upload to MongoDB after conversion
- `--env-file ENV_FILE` - Path to .env file for MongoDB config (default: .env)
- `-h, --help` - Show help message

### Workflow Options

**Option 1: One Command (Recommended)**
```bash
# Convert and upload in one go
python Canvas_Converter.py ./cs-1143 --upload
```

**Option 2: Two Commands (More Control)**
```bash
# Step 1: Convert to JSON
python Canvas_Converter.py ./cs-1143

# Step 2: Review JSON, then upload
python upload_to_mongodb.py ./cs-1143/tutor_lms_output/tutor_course.json
```

**When to use each:**
- Use **Option 1** for quick end-to-end workflow
- Use **Option 2** to review JSON before uploading or upload old conversions

## 📂 Output Structure

```
tutor_lms_output/
├── tutor_course.json          # Complete course structure
├── migration_report.json      # Machine-readable report
├── migration_report.html      # Human-readable report
└── IMPORT_INSTRUCTIONS.md     # Import guide
```

## 📤 MongoDB Upload (Optional)

After converting a course, you can upload it directly to MongoDB.

### Setup

1. **Install MongoDB dependencies** (if not already installed):
```bash
pip install -r requirements.txt
```

2. **Configure MongoDB connection**:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your MongoDB URI
# MONGODB_URI=mongodb://localhost:27017/tutor_lms
# Or for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/tutor_lms
```

### Upload Course

```bash
# Upload a converted course
python upload_to_mongodb.py ./cs-1143/tutor_lms_output/tutor_course.json

# Or specify a custom .env file
python upload_to_mongodb.py ./output/tutor_course.json --env-file .env.production
```

**Upload Script Options:**
```bash
python upload_to_mongodb.py --help
```

**Positional Arguments:**
- `course_json` - Path to tutor_course.json file (required)

**Optional Flags:**
- `--env-file ENV_FILE` - Path to .env file (default: .env)
- `-h, --help` - Show help message

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | *Required* |
| `MONGODB_DATABASE` | Database name | `tutor_lms` |
| `MONGODB_COURSE_COLLECTION` | Course collection name | `courses` |
| `MONGODB_CURRICULUM_COLLECTION` | Curriculum collection name | `curriculum_items` |

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


