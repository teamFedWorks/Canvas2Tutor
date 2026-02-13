# MongoDB Upload Guide

This guide explains how to upload converted Tutor LMS courses to MongoDB.

## Prerequisites

- MongoDB server (local or cloud-based like MongoDB Atlas)
- Python dependencies installed: `pip install -r requirements.txt`

## Quick Start

1. **Configure MongoDB connection**:
   ```bash
   cp .env.example .env
   # Edit .env and set MONGODB_URI
   ```

2. **Upload a course**:
   ```bash
   python upload_to_mongodb.py ./cs-1143/tutor_lms_output/tutor_course.json
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# MongoDB Connection URI (REQUIRED)
MONGODB_URI=mongodb://localhost:27017/tutor_lms

# Database name (optional, default: tutor_lms)
MONGODB_DATABASE=tutor_lms

# Collection names (optional)
MONGODB_COURSE_COLLECTION=courses
MONGODB_CURRICULUM_COLLECTION=curriculum_items
```

### MongoDB Atlas Example

For MongoDB Atlas cloud database:

```env
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/tutor_lms?retryWrites=true&w=majority
```

## Usage

### Basic Upload

```bash
python upload_to_mongodb.py <path_to_tutor_course.json>
```

### With Custom .env File

```bash
python upload_to_mongodb.py <path_to_tutor_course.json> --env-file .env.production
```

### Examples

```bash
# Upload from default output directory
python upload_to_mongodb.py ./cs-1143/tutor_lms_output/tutor_course.json

# Upload with custom environment file
python upload_to_mongodb.py ./output/tutor_course.json --env-file .env.staging

# Upload from different course
python upload_to_mongodb.py ./it-2420/tutor_lms_output/tutor_course.json
```

## What Gets Uploaded

The upload script creates two collections in MongoDB:

1. **Course Collection** (`courses` by default):
   - Course metadata (title, description, pricing, etc.)
   - Curriculum structure (topics and item references)
   - Author information

2. **Curriculum Collection** (`curriculum_items` by default):
   - Individual lessons, quizzes, and assignments
   - Content HTML
   - Metadata (type, slug, visibility)

## Data Transformation

The uploader automatically transforms Tutor LMS JSON to MongoDB schema:

- **Slugification**: Titles are converted to URL-friendly slugs
- **Type Detection**: Items are classified as Lesson, Quiz, or Assignment
- **ID Generation**: MongoDB ObjectIds are generated for all documents
- **References**: Proper referential integrity between courses and curriculum items

## Troubleshooting

### Connection Failed

```
[FAIL] MongoDB connection failed: ...
```

**Solutions**:
1. Verify `MONGODB_URI` is correct in `.env`
2. Check MongoDB server is running
3. Verify network connectivity and firewall settings
4. For Atlas: Check IP whitelist settings

### Environment Variable Not Set

```
[FAIL] Configuration error: MONGODB_URI environment variable is not set
```

**Solution**: Create `.env` file with `MONGODB_URI` set

### No Modules Found

```
[WARN] No modules/topics found. Check JSON structure.
```

**Solution**: Ensure the JSON file has a valid structure with `modules` or `topics` array

## Advanced Usage

### Programmatic Upload

You can also use the uploader in your Python code:

```python
from pathlib import Path
from src.config.mongodb_config import MongoDBConfig
from src.exporters.mongodb_uploader import MongoDBUploader

# Configure
config = MongoDBConfig(env_file=Path('.env'))

# Create uploader
uploader = MongoDBUploader(config)

# Connect and upload
if uploader.connect():
    uploader.upload_course(Path('./output/tutor_course.json'))
    uploader.disconnect()
```

### Custom Collection Names

Override collection names via environment variables:

```env
MONGODB_COURSE_COLLECTION=my_courses
MONGODB_CURRICULUM_COLLECTION=my_lessons
```

## Migration from JavaScript

This Python implementation replaces the previous `Coursesconvert.js` script with the following improvements:

- ✅ No Node.js dependency
- ✅ Integrated with Python pipeline
- ✅ Better error handling
- ✅ Progress reporting
- ✅ Environment-based configuration
- ✅ Type-safe implementation
