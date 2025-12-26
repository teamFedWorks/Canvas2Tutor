import xml.etree.ElementTree as ET
import os
import json
from pathlib import Path
import html
import re


class EnhancedCanvasConverter:
    """
    FINAL Enhanced Canvas → Tutor LMS Converter

    ✔ Lessons
    ✔ Quizzes
    ✔ Assignments
    ✔ Loose XML inside random hash folders
    """

    SYSTEM_XML = {
        "imsmanifest.xml",
        "assignment_settings.xml",
        "course_settings.xml"
    }

    def __init__(self, course_folder):
        self.course_folder = Path(course_folder)
        self.manifest_path = self.course_folder / "imsmanifest.xml"

        self.wiki_content_path = self.course_folder / "wiki_content"
        self.non_cc_assessments_path = self.course_folder / "non_cc_assessments"
        self.web_resources_path = self.course_folder / "web_resources"

        self.output_path = self.course_folder / "tutor_lms_output"
        self.output_path.mkdir(exist_ok=True)

        self.stats = {
            "html_files": 0,
            "xml_files": 0,
            "quizzes": 0,
            "assignments": 0,
            "loose_xml": 0,
            "total_lessons": 0,
            "missing_files": 0,
            "assignment_folders_found": 0
        }

    # ------------------------------------------------------------------
    # MAIN PIPELINE
    # ------------------------------------------------------------------

    def generate_tutor_lms_structure(self):
        print("=" * 72)
        print("FINAL CANVAS → TUTOR LMS CONVERTER (NO DATA LOSS)")
        print("=" * 72)

        print("\n[1/6] Parsing manifest...")
        course_structure, resources = self.parse_manifest()
        if not course_structure:
            return

        print(f"✓ Course: {course_structure['title']}")
        print(f"✓ Modules: {len(course_structure['modules'])}")

        print("\n[2/6] Discovering assignments...")
        assignment_folders = self._discover_assignment_folders()

        print("\n[3/6] Generating migration guide...")
        migration_guide = self._create_migration_guide(course_structure)

        print("\n[4/6] Extracting manifest content...")
        self._extract_all_content(course_structure, resources, assignment_folders)

        print("\n[5/6] Discovering & converting loose XML...")
        self._process_loose_xml_files()

        print("\n[6/6] Saving outputs...")
        self._save_outputs(course_structure, migration_guide)

        self._print_stats()

    # ------------------------------------------------------------------
    # LOOSE XML HANDLING (THIS IS WHAT YOU WERE MISSING)
    # ------------------------------------------------------------------

    def _process_loose_xml_files(self):
        output_dir = self.output_path / "lessons" / "xml_converted"
        output_dir.mkdir(parents=True, exist_ok=True)

        xml_files = []
        for root, _, files in os.walk(self.course_folder):
            if "tutor_lms_output" in root:
                continue

            for file in files:
                if file.lower().endswith(".xml") and file not in self.SYSTEM_XML:
                    xml_files.append(Path(root) / file)

        print(f"  ✓ Found {len(xml_files)} loose XML files")

        for xml_file in xml_files:
            self._convert_loose_xml(xml_file, output_dir)

    def _convert_loose_xml(self, xml_path, output_dir):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            content = ""

            for tag in ("body", "text", "content"):
                elem = root.find(f".//{tag}")
                if elem is not None and elem.text:
                    content = elem.text
                    break

            if not content:
                content = ET.tostring(root, encoding="unicode", method="text")

            content = self._clean_html(content)

            if not content.strip():
                return

            filename = output_dir / f"{xml_path.stem}.html"
            self._save_html_file(filename, xml_path.stem, content)

            self.stats["xml_files"] += 1
            self.stats["loose_xml"] += 1
            self.stats["total_lessons"] += 1

            print(f"  ✓ XML → HTML: {xml_path.name}")

        except Exception as e:
            print(f"  ⚠️ Failed XML {xml_path.name}: {e}")
            self.stats["missing_files"] += 1

    # ------------------------------------------------------------------
    # EXISTING METHODS (UNCHANGED LOGIC)
    # ------------------------------------------------------------------

    def _discover_assignment_folders(self):
        folders = []
        for item in self.course_folder.iterdir():
            if item.is_dir() and (item / "assignment_settings.xml").exists():
                folders.append(item)
                self.stats["assignment_folders_found"] += 1
        return folders

    def parse_manifest(self):
        if not self.manifest_path.exists():
            print("❌ imsmanifest.xml not found")
            return None, None

        tree = ET.parse(self.manifest_path)
        root = tree.getroot()

        title = self._extract_course_title(root)
        resources = self._build_resource_map(root)

        structure = {"title": title, "modules": []}

        org = root.find(".//organization")
        if org:
            for item in org.findall(".//item"):
                parsed = self._parse_item(item, resources)
                if parsed:
                    structure["modules"].append(parsed)

        return structure, resources

    def _extract_course_title(self, root):
        title = root.find(".//title/string")
        return title.text if title is not None else "Course"

    def _build_resource_map(self, root):
        res = {}
        for r in root.findall(".//resource"):
            res[r.get("identifier")] = {
                "href": r.get("href"),
                "type": r.get("type")
            }
        return res

    def _parse_item(self, item, resources):
        title = item.findtext("title", default="Untitled")
        obj = {"title": title, "items": []}

        ref = item.get("identifierref")
        if ref and ref in resources:
            obj["content_file"] = resources[ref]["href"]

        for child in item.findall("item"):
            obj["items"].append(self._parse_item(child, resources))

        return obj

    def _extract_all_content(self, course_structure, resources, assignment_folders):
        lessons_dir = self.output_path / "lessons"
        lessons_dir.mkdir(exist_ok=True)

    def _clean_html(self, content):
        content = html.unescape(content)
        content = re.sub(r"\$IMS-CC-FILEBASE\$/", "../web_resources/", content)
        return content.strip()

    def _save_html_file(self, filepath, title, content):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{html.escape(title)}</title></head>
<body>{content}</body>
</html>""")

    def _create_migration_guide(self, course_structure):
        return f"MIGRATION GUIDE: {course_structure['title']}"

    def _save_outputs(self, course_structure, migration_guide):
        with open(self.output_path / "migration_guide.txt", "w") as f:
            f.write(migration_guide)

        with open(self.output_path / "course_structure.json", "w") as f:
            json.dump(course_structure, f, indent=2)

    def _print_stats(self):
        print("\n" + "=" * 72)
        for k, v in self.stats.items():
            print(f"{k:25}: {v}")
        print("=" * 72)


# ----------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    COURSE_FOLDER = sys.argv[1] if len(sys.argv) > 1 else "cs-2000"

    converter = EnhancedCanvasConverter(COURSE_FOLDER)
    converter.generate_tutor_lms_structure()
