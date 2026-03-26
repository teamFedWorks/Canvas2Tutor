#!/usr/bin/env python3
"""
Course Ingestion Validation Script — auto-runs after every ingestion.

Every warning explains WHY it exists and EXACTLY what manual action is needed.
The (M/D) date notation in module titles is the class meeting date (Month/Day).

Usage:
  python scripts/validate_ingestion.py --course-id <mongo_id>
  python scripts/validate_ingestion.py --slug <course-slug>
  python scripts/validate_ingestion.py --course-id <id> --strict
"""
import sys, os, json, argparse, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import boto3, bson
from pymongo import MongoClient
from botocore.exceptions import ClientError

class Status(str, Enum):
    PASS="PASS"; FAIL="FAIL"; RETRY="RETRY"; WARN="WARN"; SKIP="SKIP"

ICON = {Status.PASS:"[PASS]",Status.FAIL:"[FAIL]",Status.RETRY:"[RETRY]",Status.WARN:"[WARN]",Status.SKIP:"[SKIP]"}

@dataclass
class CheckResult:
    name: str; status: Status; value: str=""; why: str=""; action: str=""

@dataclass
class ItemResult:
    title: str; item_type: str; status: Status
    detail: str=""; why: str=""; action: str=""; attachments: int=0

@dataclass
class ModuleResult:
    title: str; week_label: str; status: Status
    item_count: int=0; items: List[ItemResult]=field(default_factory=list)
    issues: List[str]=field(default_factory=list)

@dataclass
class AssetResult:
    name: str; url: str; status: Status; size_bytes: int=0; detail: str=""

@dataclass
class ValidationReport:
    course_id: str; course_title: str; slug: str
    course_code: str=""; department: str=""
    generated_at: str=field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    strict: bool=False
    structure_checks: List[CheckResult]=field(default_factory=list)
    module_results:   List[ModuleResult]=field(default_factory=list)
    asset_results:    List[AssetResult]=field(default_factory=list)
    metadata_checks:  List[CheckResult]=field(default_factory=list)
    total_modules: int=0; total_items: int=0; total_assets: int=0
    assets_pass: int=0; assets_fail: int=0; assets_retry: int=0
    verdict: Status=Status.WARN; verdict_label: str=""; verdict_reason: str=""
    manual_tasks: List[str]=field(default_factory=list)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _mongo():
    uri = os.getenv("MONGODB_URI")
    if not uri: raise ValueError("MONGODB_URI not set")
    return MongoClient(uri)

def fetch_course(ident: str, by_slug=False) -> Optional[Dict]:
    col = _mongo()[os.getenv("MONGODB_DATABASE","lms_db")]["courses"]
    if by_slug: return col.find_one({"slug": ident})
    try:    return col.find_one({"_id": bson.ObjectId(ident)})
    except: return col.find_one({"slug": ident})

def _s3():
    return boto3.client("s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION","us-east-1"))

def _head(s3c, bucket, url) -> Tuple[Status,int,str]:
    cdn = os.getenv("CDN_URL","").rstrip("/")
    if cdn and url.startswith(cdn):
        key = url[len(cdn):].lstrip("/")
    elif f"{bucket}.s3" in url:
        key = re.sub(r"^https?://[^/]+/","",url)
    else:
        return Status.SKIP,0,"URL outside known CDN domain — cannot verify"
    try:
        r = s3c.head_object(Bucket=bucket, Key=key)
        sz = r.get("ContentLength",0)
        if sz==0: return Status.RETRY,0,"File exists in S3 but is 0 bytes — upload may have been interrupted"
        return Status.PASS,sz,f"Confirmed in S3 — {sz:,} bytes"
    except ClientError as e:
        c = e.response["Error"]["Code"]
        if c in ("404","NoSuchKey"): return Status.FAIL,0,"File NOT found in S3 — upload failed or was skipped"
        if c=="403":                 return Status.FAIL,0,"Access denied — check S3 bucket policy"
        return Status.FAIL,0,f"S3 error: {c}"

def _sz(n):
    for u in ("B","KB","MB","GB"):
        if n<1024: return f"{n:.1f} {u}"
        n//=1024
    return f"{n:.1f} TB"

def _week_label(title: str) -> str:
    """
    Convert Canvas module titles like 'Week 1 (9/9) - Introduction'
    to human-readable labels like 'Week 1 — Sep 9 — Introduction'.
    The (M/D) in Canvas titles is the class meeting date (Month/Day).
    """
    months = {"1":"Jan","2":"Feb","3":"Mar","4":"Apr","5":"May","6":"Jun",
              "7":"Jul","8":"Aug","9":"Sep","10":"Oct","11":"Nov","12":"Dec"}
    def repl(m):
        return f"— {months.get(m.group(1), m.group(1))} {m.group(2)}"
    label = re.sub(r'\((\d{1,2})/(\d{1,2})\)', repl, title)
    label = re.sub(r'\s*-\s*', ' — ', label).strip()
    return label

# ── Validation sections ───────────────────────────────────────────────────────

def validate_structure(course: Dict) -> List[CheckResult]:
    fields = {
        "title":            "Course Title",
        "slug":             "URL Slug",
        "courseUrl":        "Course URL",
        "university":       "University ID",
        "authorId":         "Author / Instructor ID",
        "curriculum":       "Curriculum (modules list)",
        "status":           "Publication Status",
        "description":      "Full Description",
        "shortDescription": "Short Description",
    }
    out = []
    for f, label in fields.items():
        val = course.get(f)
        empty = val is None or val=="" or val==[]
        out.append(CheckResult(
            name=label,
            status=Status.FAIL if empty else Status.PASS,
            value="MISSING" if empty else (f"{len(val)} module(s)" if isinstance(val,list) else str(val)[:90]),
            why="Required field — course cannot display correctly without it." if empty else "",
            action=f"Populate the '{f}' field before publishing." if empty else ""
        ))
    return out

def validate_modules(course: Dict) -> Tuple[List[ModuleResult],int,int]:
    results, total_items = [], 0
    non_renderable = (".ipynb",".csv",".rb",".py",".js",".json",".zip",".txt")
    respondus_kw   = ("respondus","lockdown","proctored","ldb")

    for mod in course.get("curriculum",[]):
        raw   = mod.get("title","Untitled Module")
        label = _week_label(raw)
        items = mod.get("items",[])
        total_items += len(items)
        issues, item_results = [], []

        if not items:
            issues.append(
                "This module contains no lessons or activities. "
                "In Canvas, this module existed but had no content items linked to it. "
                "No action is needed unless you expected content here."
            )

        for item in items:
            t     = item.get("title","Untitled")
            itype = item.get("type","Unknown")
            body  = item.get("content","")
            atts  = item.get("attachments",[])
            has_body = bool(body and body.strip())
            has_atts = len(atts)>0
            is_respondus = any(k in t.lower() for k in respondus_kw)
            is_download  = any(t.lower().endswith(e) for e in non_renderable)

            if is_respondus:
                item_results.append(ItemResult(
                    title=t, item_type=itype, status=Status.WARN,
                    detail="Proctored exam — Respondus LockDown Browser required",
                    why=(
                        "This quiz is protected by Respondus LockDown Browser, a third-party "
                        "proctoring tool. Canvas does not include the actual quiz questions in "
                        "the export package — they are locked inside Respondus's system. "
                        "This is a Canvas/Respondus limitation, not a pipeline bug."
                    ),
                    action=(
                        "MANUAL ACTION REQUIRED: Log into the target LMS, open this quiz, "
                        "and either (a) re-enter the questions manually, or (b) configure it "
                        "as an external LTI tool pointing to your Respondus account."
                    ),
                    attachments=len(atts)
                ))
            elif is_download and has_atts:
                item_results.append(ItemResult(
                    title=t, item_type=itype, status=Status.PASS,
                    detail=f"Downloadable file — {len(atts)} file(s) uploaded to S3",
                    why="This is a data or code file (e.g. Jupyter notebook, CSV dataset). It has no HTML body — that is correct. Students download it directly.",
                    attachments=len(atts)
                ))
            elif not has_body and not has_atts:
                item_results.append(ItemResult(
                    title=t, item_type=itype, status=Status.WARN,
                    detail="No content body and no files attached",
                    why=(
                        "The pipeline could not find any content or file for this item. "
                        "This usually means the original Canvas export did not include the file, "
                        "or the file type is not yet supported."
                    ),
                    action="Check the original Canvas course for this item. If the file exists, re-export from Canvas and re-ingest with --force.",
                    attachments=0
                ))
            elif itype=="Quiz" and not item.get("quizConfig"):
                item_results.append(ItemResult(
                    title=t, item_type=itype, status=Status.WARN,
                    detail="Quiz imported but settings not configured",
                    why="The quiz content was imported but the configuration block (time limit, attempts, passing score) is missing.",
                    action="Open this quiz in the LMS and configure: time limit, allowed attempts, and passing score.",
                    attachments=len(atts)
                ))
            else:
                detail = f"{len(atts)} file(s) attached to this item" if has_atts else "Content imported successfully"
                item_results.append(ItemResult(
                    title=t, item_type=itype, status=Status.PASS,
                    detail=detail, attachments=len(atts)
                ))

        warns = sum(1 for i in item_results if i.status==Status.WARN)
        fails = sum(1 for i in item_results if i.status==Status.FAIL)
        mod_status = Status.FAIL if fails else (Status.WARN if (warns or issues) else Status.PASS)
        results.append(ModuleResult(title=raw, week_label=label, status=mod_status,
                                    item_count=len(items), items=item_results, issues=issues))

    return results, len(course.get("curriculum",[])), total_items

def validate_assets(course: Dict, bucket: str) -> Tuple[List[AssetResult],int,int,int]:
    s3c = _s3()
    out, seen = [], set()
    p=f=r=0
    for mod in course.get("curriculum",[]):
        for item in mod.get("items",[]):
            for att in item.get("attachments",[]):
                url = att.get("url","")
                if not url or url in seen: continue
                seen.add(url)
                st,sz,detail = _head(s3c,bucket,url)
                out.append(AssetResult(name=att.get("name",url.split("/")[-1]),
                                       url=url,status=st,size_bytes=sz,detail=detail))
                if st==Status.PASS:  p+=1
                elif st==Status.FAIL: f+=1
                elif st==Status.RETRY: r+=1
    return out,p,f,r

def validate_metadata(course: Dict) -> List[CheckResult]:
    out = []
    img = course.get("featuredImage","")
    if not img or "placehold.co" in img:
        out.append(CheckResult("Course Thumbnail", Status.WARN,
            value="Placeholder image (no thumbnail in Canvas export)",
            why="Canvas exports do not include a course thumbnail. A placeholder is used so the course can be published, but it looks unprofessional in the course catalogue.",
            action="MANUAL ACTION: Ask the course author for a cover image (JPG/PNG, 600×400 px minimum). Upload it to S3 and update the 'featuredImage' field."))
    else:
        out.append(CheckResult("Course Thumbnail", Status.PASS, value=img[:80]))

    code = course.get("courseCode","")
    if not code or code=="IMPORTED":
        out.append(CheckResult("Course Code", Status.WARN,
            value=f"'{code}' — could not auto-detect",
            why="The course code could not be extracted from the title automatically.",
            action="Set the correct course code (e.g. IT-1104) in the course record."))
    else:
        out.append(CheckResult("Course Code", Status.PASS, value=code,
            why="Auto-detected from course title."))

    dept = course.get("department","")
    if not dept or dept=="Imported":
        out.append(CheckResult("Department", Status.WARN,
            value=f"'{dept}' — could not auto-detect",
            why="Department was not auto-detected from the course code prefix.",
            action="Set the correct department name in the course record."))
    else:
        out.append(CheckResult("Department", Status.PASS, value=dept,
            why="Auto-detected from course code prefix."))

    desc = course.get("description","")
    if len(desc)<30:
        out.append(CheckResult("Course Description", Status.WARN,
            value=f"{len(desc)} characters — too short",
            why="The description is auto-generated and not meaningful to students browsing the catalogue.",
            action="Write a proper course description (at least 100 characters) explaining what students will learn."))
    else:
        out.append(CheckResult("Course Description", Status.PASS, value=f"{len(desc)} characters"))

    return out

def compute_verdict(report: ValidationReport, strict: bool) -> Tuple[Status,str,str]:
    all_items = [CheckResult(i.title,i.status) for m in report.module_results for i in m.items]
    all_checks = report.structure_checks + report.metadata_checks + all_items
    fails = sum(1 for c in all_checks if c.status==Status.FAIL)
    warns = sum(1 for c in all_checks if c.status==Status.WARN)
    if fails>0 or report.assets_fail>0:
        parts = []
        if fails: parts.append(f"{fails} required field(s) missing")
        if report.assets_fail: parts.append(f"{report.assets_fail} asset(s) missing from S3")
        return Status.FAIL,"[FAIL] Course Ingestion FAILED"," and ".join(parts)
    if warns>0 or report.assets_retry>0:
        parts = []
        if warns: parts.append(f"{warns} item(s) need manual attention (see tasks below)")
        if report.assets_retry: parts.append(f"{report.assets_retry} asset(s) need re-upload")
        return Status.WARN,"[WARN] Course Ingestion PARTIALLY COMPLETE"," — ".join(parts)
    return Status.PASS,"[PASS] Course Ingestion COMPLETE and VALID","All checks passed. Course is ready to publish."

def build_manual_tasks(report: ValidationReport) -> List[str]:
    tasks = []
    for m in report.module_results:
        for i in m.items:
            if i.action:
                tasks.append(f"[{m.week_label}  ›  {i.title}]\n   {i.action}")
    for a in report.asset_results:
        if a.status==Status.FAIL:
            tasks.append(f"[S3 Upload]  Re-upload missing file: {a.name}\n   URL was: {a.url}")
        elif a.status==Status.RETRY:
            tasks.append(f"[S3 Upload]  File is 0 bytes — re-upload: {a.name}")
    for c in report.metadata_checks:
        if c.action:
            tasks.append(f"[Metadata]  {c.action}")
    return list(dict.fromkeys(tasks))

# ── HTML report ───────────────────────────────────────────────────────────────

def _mapping_summary(r: ValidationReport) -> str:
    """
    Build the Course Mapping Status section — a visual table showing
    every Canvas content type and how it mapped into the LMS.
    """
    # Count by type across all modules
    counts = {"Lesson": [0,0], "Quiz": [0,0], "Assignment": [0,0], "Other": [0,0]}
    # [pass_count, warn_count]
    for m in r.module_results:
        for i in m.items:
            key = i.item_type if i.item_type in counts else "Other"
            if i.status == Status.PASS:
                counts[key][0] += 1
            else:
                counts[key][1] += 1

    total_pass  = sum(v[0] for v in counts.values())
    total_warn  = sum(v[1] for v in counts.values())
    total_items = total_pass + total_warn
    pct = round(total_pass / total_items * 100) if total_items else 0

    canvas_types = {
        "Lesson":     ("webcontent / wiki page / HTML",   "LMS Lesson (HTML content)"),
        "Quiz":       ("imsqti assessment / QTI XML",     "LMS Quiz (with quizConfig)"),
        "Assignment": ("canvas:assignment XML",           "LMS Assignment (with assignmentConfig)"),
        "Other":      ("discussion / weblink / download", "LMS Lesson (embedded link or attachment)"),
    }

    rows = ""
    for lms_type, (canvas_src, lms_dest) in canvas_types.items():
        p, w = counts[lms_type]
        total = p + w
        if total == 0:
            continue
        bar_pct = round(p / total * 100) if total else 0
        status_cell = (
            f'<span style="background:#e8f5e9;color:#2e7d32;border:1px solid #2e7d32;'
            f'padding:2px 8px;border-radius:6px;font-size:0.78em;font-weight:700">PASS</span>'
            if w == 0 else
            f'<span style="background:#fffde7;color:#f57f17;border:1px solid #f57f17;'
            f'padding:2px 8px;border-radius:6px;font-size:0.78em;font-weight:700">'
            f'{w} item(s) need attention</span>'
        )
        bar = (
            f'<div style="background:#e0e0e0;border-radius:4px;height:8px;width:120px;'
            f'display:inline-block;vertical-align:middle;margin-right:6px">'
            f'<div style="background:#2e7d32;width:{bar_pct}%;height:100%;border-radius:4px"></div></div>'
            f'<span style="font-size:0.8em;color:#555">{p}/{total} mapped ({bar_pct}%)</span>'
        )
        rows += (
            f"<tr>"
            f"<td style='font-weight:600;color:#1a1a2e'>{lms_type}</td>"
            f"<td style='font-size:0.82em;color:#555'>{canvas_src}</td>"
            f"<td style='font-size:0.82em;color:#1565c0'>{lms_dest}</td>"
            f"<td>{bar}</td>"
            f"<td>{status_cell}</td>"
            f"</tr>"
        )

    overall_bar = (
        f'<div style="background:#e0e0e0;border-radius:6px;height:12px;width:100%;margin:8px 0">'
        f'<div style="background:{"#2e7d32" if pct==100 else "#f57f17"};'
        f'width:{pct}%;height:100%;border-radius:6px;transition:width .3s"></div></div>'
    )
    overall_color = "#2e7d32" if pct == 100 else "#e65100"

    return f"""
    <div style="background:#fff;border-radius:8px;padding:20px 24px;
                box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div>
          <div style="font-size:1em;font-weight:700;color:#1a1a2e">
            Overall Mapping Coverage
          </div>
          <div style="font-size:0.82em;color:#666;margin-top:2px">
            {total_pass} of {total_items} content items successfully mapped from Canvas to LMS
          </div>
        </div>
        <div style="font-size:2.4em;font-weight:800;color:{overall_color}">{pct}%</div>
      </div>
      {overall_bar}
      <table style="width:100%;border-collapse:collapse;font-size:0.88em;margin-top:16px">
        <thead>
          <tr style="background:#f5f5f5">
            <th style="padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid #ddd;font-size:0.83em;text-transform:uppercase;letter-spacing:.03em">LMS Content Type</th>
            <th style="padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid #ddd;font-size:0.83em;text-transform:uppercase;letter-spacing:.03em">Canvas Source Format</th>
            <th style="padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid #ddd;font-size:0.83em;text-transform:uppercase;letter-spacing:.03em">Mapped To</th>
            <th style="padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid #ddd;font-size:0.83em;text-transform:uppercase;letter-spacing:.03em">Coverage</th>
            <th style="padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid #ddd;font-size:0.83em;text-transform:uppercase;letter-spacing:.03em">Mapping Status</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def generate_html(r: ValidationReport) -> str:
    vc = {"PASS":"#2e7d32","FAIL":"#c62828","WARN":"#e65100"}.get(r.verdict.value,"#555")

    def badge(s: Status, label=None) -> str:
        bg = {"PASS":"#e8f5e9","FAIL":"#ffebee","RETRY":"#fff3e0","WARN":"#fffde7","SKIP":"#f5f5f5"}
        fg = {"PASS":"#2e7d32","FAIL":"#c62828","RETRY":"#e65100","WARN":"#f57f17","SKIP":"#757575"}
        b,f = bg.get(s.value,"#f5f5f5"), fg.get(s.value,"#555")
        txt = label or s.value
        return (f'<span style="background:{b};color:{f};border:1px solid {f};'
                f'padding:3px 10px;border-radius:10px;font-size:0.78em;font-weight:700;white-space:nowrap">'
                f'{txt}</span>')

    def tooltip(text: str) -> str:
        if not text: return ""
        safe = text.replace('"','&quot;').replace("'","&#39;")
        return (f'<span title="{safe}" style="cursor:help;color:#1565c0;font-size:0.8em;'
                f'margin-left:6px;border-bottom:1px dotted #1565c0">why?</span>')

    def action_box(action: str) -> str:
        if not action: return ""
        return (f'<div style="margin-top:6px;background:#fff8e1;border-left:3px solid #f57f17;'
                f'padding:8px 12px;border-radius:4px;font-size:0.82em;color:#444">'
                f'<strong style="color:#e65100">Action Required:</strong> {action}</div>')

    # ── stat cards ──
    def stat(n, label, color="#1a1a2e"):
        return (f'<div style="background:#fff;border-radius:8px;padding:14px 20px;text-align:center;'
                f'box-shadow:0 1px 3px rgba(0,0,0,.1);min-width:110px">'
                f'<div style="font-size:2.2em;font-weight:700;color:{color}">{n}</div>'
                f'<div style="font-size:0.75em;color:#666;margin-top:3px">{label}</div></div>')

    stats_html = (
        stat(r.total_modules,"Modules") +
        stat(r.total_items,"Lessons & Activities") +
        stat(r.total_assets,"Assets Checked") +
        stat(r.assets_pass,"Assets Passed","#2e7d32") +
        stat(r.assets_fail,"Assets Failed","#c62828") +
        stat(r.assets_retry,"Assets Retry","#e65100")
    )

    # ── structure table ──
    struct_rows = ""
    for c in r.structure_checks:
        struct_rows += (
            f"<tr><td style='font-weight:500'>{c.name}</td>"
            f"<td>{badge(c.status)}</td>"
            f"<td style='font-size:0.85em;color:#444'>{c.value}{tooltip(c.why)}</td>"
            f"<td>{action_box(c.action)}</td></tr>"
        )

    # ── module sections ──
    mod_html = ""
    for m in r.module_results:
        bc = "#2e7d32" if m.status==Status.PASS else "#e65100"
        issue_html = "".join(
            f'<div style="background:#fff8e1;border-left:3px solid #f57f17;padding:8px 12px;'
            f'margin-bottom:8px;border-radius:4px;font-size:0.83em;color:#555">'
            f'<strong>Note:</strong> {iss}</div>'
            for iss in m.issues
        )
        item_rows = ""
        for i in m.items:
            type_badge = (
                f'<span style="background:#e3f2fd;color:#1565c0;padding:1px 7px;'
                f'border-radius:8px;font-size:0.75em;font-weight:600;margin-right:6px">{i.item_type}</span>'
            )
            item_rows += (
                f"<tr>"
                f"<td style='font-size:0.85em'>{type_badge}{i.title}</td>"
                f"<td style='white-space:nowrap'>{badge(i.status)}</td>"
                f"<td style='font-size:0.82em;color:#555'>{i.detail}{tooltip(i.why)}</td>"
                f"<td style='font-size:0.82em'>"
            )
            if i.attachments:
                item_rows += f'<span style="color:#2e7d32">{i.attachments} file(s) in S3</span>'
            item_rows += action_box(i.action) + "</td></tr>"
        mod_html += f"""
        <div style="margin-bottom:18px;border-left:4px solid {bc};padding:14px 18px;
                    background:#fff;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
            {badge(m.status)}
            <div>
              <div style="font-weight:700;font-size:1em;color:#1a1a2e">{m.week_label}</div>
              <div style="font-size:0.78em;color:#888;margin-top:1px">
                Original Canvas title: <em>{m.title}</em> &nbsp;·&nbsp; {m.item_count} item(s)
              </div>
            </div>
          </div>
          {issue_html}
          <table style="width:100%;border-collapse:collapse;font-size:0.88em">
            <thead><tr style="background:#f8f9fa">
              <th style="padding:6px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e0e0e0">Lesson / Activity</th>
              <th style="padding:6px 10px;font-weight:600;border-bottom:2px solid #e0e0e0">Status</th>
              <th style="padding:6px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e0e0e0">Detail</th>
              <th style="padding:6px 10px;text-align:left;font-weight:600;border-bottom:2px solid #e0e0e0">Action Required</th>
            </tr></thead>
            <tbody>{item_rows}</tbody>
          </table>
        </div>"""

    # ── asset table ──
    asset_rows = ""
    for a in r.asset_results:
        asset_rows += (
            f"<tr>"
            f"<td style='font-size:0.82em;word-break:break-all'>{a.name}</td>"
            f"<td>{badge(a.status)}</td>"
            f"<td style='font-size:0.82em'>{_sz(a.size_bytes) if a.size_bytes else '—'}</td>"
            f"<td style='font-size:0.82em;color:#555'>{a.detail}</td>"
            f"<td style='font-size:0.75em;word-break:break-all'>"
            f"<a href='{a.url}' target='_blank' style='color:#1565c0'>{a.url}</a></td>"
            f"</tr>"
        )
    if not asset_rows:
        asset_rows = "<tr><td colspan='5' style='color:#999;font-style:italic;padding:12px'>No assets found in this course.</td></tr>"

    # ── metadata table ──
    meta_rows = ""
    for c in r.metadata_checks:
        meta_rows += (
            f"<tr><td style='font-weight:500'>{c.name}</td>"
            f"<td>{badge(c.status)}</td>"
            f"<td style='font-size:0.85em;color:#444'>{c.value}{tooltip(c.why)}</td>"
            f"<td>{action_box(c.action)}</td></tr>"
        )

    # ── manual tasks ──
    if r.manual_tasks:
        tasks_html = "".join(
            f'<div style="background:#fff;border:1px solid #e0e0e0;border-left:4px solid #e65100;'
            f'border-radius:6px;padding:12px 16px;margin-bottom:10px">'
            f'<div style="font-size:0.85em;color:#333;white-space:pre-wrap">'
            f'<strong style="color:#e65100">Task {i}.</strong> {t}</div></div>'
            for i,t in enumerate(r.manual_tasks,1)
        )
    else:
        tasks_html = ('<div style="background:#e8f5e9;border-left:4px solid #2e7d32;'
                      'padding:12px 16px;border-radius:6px;color:#2e7d32;font-weight:600">'
                      'No manual tasks required — course is fully automated.</div>')

    # ── legend ──
    legend = """
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;background:#fff;
                border-radius:8px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:24px">
      <div style="display:flex;gap:10px;align-items:flex-start;font-size:0.83em;color:#444">
        <span style="background:#e8f5e9;color:#2e7d32;border:1px solid #2e7d32;padding:2px 8px;border-radius:8px;font-weight:700;white-space:nowrap">PASS</span>
        <span>Item was successfully imported. No action needed.</span>
      </div>
      <div style="display:flex;gap:10px;align-items:flex-start;font-size:0.83em;color:#444">
        <span style="background:#ffebee;color:#c62828;border:1px solid #c62828;padding:2px 8px;border-radius:8px;font-weight:700;white-space:nowrap">FAIL</span>
        <span>Critical error — item is broken or missing. Must be fixed before publishing.</span>
      </div>
      <div style="display:flex;gap:10px;align-items:flex-start;font-size:0.83em;color:#444">
        <span style="background:#fffde7;color:#f57f17;border:1px solid #f57f17;padding:2px 8px;border-radius:8px;font-weight:700;white-space:nowrap">WARN</span>
        <span>Item imported but needs manual attention. Hover the "why?" link for details.</span>
      </div>
      <div style="display:flex;gap:10px;align-items:flex-start;font-size:0.83em;color:#444">
        <span style="background:#fff3e0;color:#e65100;border:1px solid #e65100;padding:2px 8px;border-radius:8px;font-weight:700;white-space:nowrap">RETRY</span>
        <span>Asset uploaded but is 0 bytes. Re-run the ingestion to fix.</span>
      </div>
    </div>"""

    ts = datetime.fromisoformat(r.generated_at.replace("Z","")).strftime("%B %d, %Y at %H:%M UTC") \
         if r.generated_at else r.generated_at

    mapping_html = _mapping_summary(r)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Ingestion Report — {r.course_title}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
          background:#f0f2f5;color:#212529;padding:28px}}
    .wrap{{max-width:1280px;margin:0 auto}}
    h1{{font-size:1.7em;color:#1a1a2e;margin-bottom:4px}}
    .sub{{color:#666;font-size:0.85em;margin-bottom:16px;line-height:1.7}}
    h2{{font-size:1.05em;margin:28px 0 12px;color:#333;
        border-bottom:2px solid #e0e0e0;padding-bottom:6px;text-transform:uppercase;
        letter-spacing:.04em}}
    table{{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;
           overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:8px}}
    th{{background:#f5f5f5;padding:8px 12px;text-align:left;font-weight:600;
        border-bottom:2px solid #ddd;font-size:0.83em;text-transform:uppercase;letter-spacing:.03em}}
    td{{padding:8px 12px;border-bottom:1px solid #f0f0f0;vertical-align:top}}
    tr:last-child td{{border-bottom:none}}
    .verdict{{padding:18px 22px;border-radius:8px;font-size:1.15em;font-weight:700;
              border-left:6px solid {vc};background:#fff;margin-top:28px;
              box-shadow:0 1px 4px rgba(0,0,0,.1)}}
    .verdict-reason{{font-size:0.85em;font-weight:400;color:#555;margin-top:6px;line-height:1.5}}
    .stats{{display:flex;gap:14px;margin-bottom:24px;flex-wrap:wrap}}
    .pdf-btn{{display:inline-block;background:#1a1a2e;color:#fff;border:none;
              border-radius:6px;padding:10px 22px;font-size:0.9em;font-weight:600;
              cursor:pointer;letter-spacing:.02em;margin-bottom:20px;
              box-shadow:0 2px 6px rgba(0,0,0,.2);text-decoration:none}}
    .pdf-btn:hover{{background:#2d2d4e}}
    @media print{{
      body{{background:#fff;padding:16px;font-size:11pt}}
      .pdf-btn{{display:none!important}}
      .wrap{{max-width:100%}}
      h2{{margin-top:18px}}
      table{{box-shadow:none;border:1px solid #ccc;page-break-inside:avoid}}
      .verdict{{box-shadow:none;border:1px solid #ccc}}
      .stats > div{{box-shadow:none;border:1px solid #ddd}}
      /* Show full URL after every link so PDFs have clickable/readable URLs */
      a[href]:after{{
        content:" (" attr(href) ")";
        font-size:0.78em;
        color:#555;
        word-break:break-all;
      }}
      /* Don't expand tooltip spans or internal anchors */
      a[href^="#"]:after,
      span[title]:after{{content:""}}
      /* Asset URL cells already show the full URL as link text — don't repeat */
      td a[href^="http"]:after{{content:""}}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px">
    <h1>Course Ingestion Validation Report</h1>
    <button class="pdf-btn" onclick="window.print()">Download as PDF</button>
  </div>

  <div class="sub">
    <strong>Course:</strong> {r.course_title} &nbsp;·&nbsp;
    <strong>Code:</strong> {r.course_code or "—"} &nbsp;·&nbsp;
    <strong>Department:</strong> {r.department or "—"}<br>
    <strong>MongoDB ID:</strong> <code>{r.course_id}</code> &nbsp;·&nbsp;
    <strong>Slug:</strong> <code>{r.slug}</code> &nbsp;·&nbsp;
    <strong>Mode:</strong> {"STRICT" if r.strict else "STANDARD"} &nbsp;·&nbsp;
    <strong>Generated:</strong> {ts}
  </div>

  <div class="stats">{stats_html}</div>

  <h2>How to Read This Report</h2>
  {legend}

  <h2>1 · Course Mapping Status</h2>
  <p style="font-size:0.83em;color:#666;margin-bottom:12px">
    Shows how each Canvas content type was translated into the LMS schema.
    A 100% coverage means every item in the manifest was successfully mapped.
    Items below 100% indicate content that needs manual attention (see Section 5).
  </p>
  {mapping_html}

  <h2>2 · Course Structure Integrity</h2>
  <p style="font-size:0.83em;color:#666;margin-bottom:10px">
    Verifies that all required database fields are present and populated.
  </p>
  <table><thead><tr><th>Field</th><th>Status</th><th>Value</th><th>Action</th></tr></thead>
  <tbody>{struct_rows}</tbody></table>

  <h2>3 · Module &amp; Component Validation</h2>
  <p style="font-size:0.83em;color:#666;margin-bottom:12px">
    <strong>Note on dates:</strong> Module titles like <em>"Week 1 (9/9)"</em> use the
    Canvas convention of <em>(Month/Day)</em> to indicate the class meeting date.
    This report converts them to readable labels (e.g. <em>Sep 9</em>) for clarity.
    The original Canvas title is shown in grey below each module heading.
  </p>
  {mod_html if mod_html else "<p style='color:#999;font-style:italic'>No modules found.</p>"}

  <h2>4 · Asset Storage Validation (S3)</h2>
  <p style="font-size:0.83em;color:#666;margin-bottom:10px">
    Every file attached to a lesson is HEAD-checked against the S3 bucket
    <strong>{os.getenv("S3_CDN_BUCKET","—")}</strong> to confirm it was uploaded successfully.
  </p>
  <table><thead><tr><th>File Name</th><th>Status</th><th>Size</th><th>Detail</th><th>S3 URL</th></tr></thead>
  <tbody>{asset_rows}</tbody></table>

  <h2>5 · Thumbnail &amp; Metadata Validation</h2>
  <p style="font-size:0.83em;color:#666;margin-bottom:10px">
    Checks course metadata quality. Items marked WARN are functional but need enrichment.
  </p>
  <table><thead><tr><th>Check</th><th>Status</th><th>Current Value</th><th>Action</th></tr></thead>
  <tbody>{meta_rows}</tbody></table>

  <h2>6 · Manual Tasks Checklist</h2>
  <p style="font-size:0.83em;color:#666;margin-bottom:12px">
    These are the <strong>only remaining items that require human action</strong>.
    Everything else was handled automatically by the pipeline.
  </p>
  {tasks_html}

  <div class="verdict">
    {r.verdict_label}
    <div class="verdict-reason">{r.verdict_reason}</div>
  </div>

</div>
</body>
</html>"""

# ── Core runner (called by CLI and by ingestion worker) ──────────────────────

def run_validation(identifier: str, by_slug=False, strict=False, quiet=False) -> ValidationReport:
    def log(msg):
        if not quiet:
            try: print(msg)
            except UnicodeEncodeError: pass

    log(f"\n[*] Fetching course from MongoDB...")
    course = fetch_course(identifier, by_slug=by_slug)
    if not course:
        print(f"Course not found: {identifier}")
        sys.exit(1)

    course_id    = str(course.get("_id",""))
    course_title = course.get("title","Unknown")
    slug         = course.get("slug","")
    s3_bucket    = os.getenv("S3_CDN_BUCKET","")

    rep = ValidationReport(
        course_id=course_id, course_title=course_title, slug=slug,
        course_code=course.get("courseCode",""), department=course.get("department",""),
        strict=strict
    )
    log(f"    Found: {course_title}  (slug: {slug})")
    log("[*] Validating course structure...")
    rep.structure_checks = validate_structure(course)
    log("[*] Validating modules and items...")
    rep.module_results, rep.total_modules, rep.total_items = validate_modules(course)

    if s3_bucket:
        log(f"[*] Checking S3 assets in bucket '{s3_bucket}'...")
        rep.asset_results, rep.assets_pass, rep.assets_fail, rep.assets_retry = \
            validate_assets(course, s3_bucket)
        rep.total_assets = len(rep.asset_results)
    else:
        log("[!] S3_CDN_BUCKET not set — skipping asset validation")

    log("[*] Validating metadata and thumbnails...")
    rep.metadata_checks = validate_metadata(course)
    rep.verdict, rep.verdict_label, rep.verdict_reason = compute_verdict(rep, strict)
    rep.manual_tasks = build_manual_tasks(rep)
    return rep


def save_report(rep: ValidationReport, out_dir: Path, emit_json=True) -> Path:
    """Save HTML (always) and optionally JSON. Returns HTML path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w-]","_", rep.slug or rep.course_id)
    html_path = out_dir / f"validation_{safe}.html"
    html_path.write_text(generate_html(rep), encoding="utf-8")
    if emit_json:
        from dataclasses import asdict
        def _s(o): return o.value if isinstance(o,Status) else (_ for _ in ()).throw(TypeError(str(type(o))))
        (out_dir / f"validation_{safe}.json").write_text(
            json.dumps(asdict(rep), indent=2, default=_s), encoding="utf-8")
    return html_path


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Validate a course ingestion result")
    g  = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--course-id", help="MongoDB ObjectId")
    g.add_argument("--slug",      help="Course slug")
    ap.add_argument("--strict",   action="store_true")
    ap.add_argument("--no-json",  action="store_true", help="Skip JSON output")
    args = ap.parse_args()

    rep = run_validation(args.slug or args.course_id,
                         by_slug=args.slug is not None, strict=args.strict)

    # Console summary
    print(f"\n{'='*70}")
    print(f"  {rep.verdict_label}")
    print(f"  {rep.verdict_reason}")
    print(f"  Modules: {rep.total_modules}  Items: {rep.total_items}  "
          f"Assets: {rep.total_assets} (PASS:{rep.assets_pass} FAIL:{rep.assets_fail} RETRY:{rep.assets_retry})")
    if rep.manual_tasks:
        print(f"\n  {len(rep.manual_tasks)} manual task(s) required:")
        for i,t in enumerate(rep.manual_tasks,1):
            print(f"     {i}. {t.splitlines()[0]}")
    print(f"{'='*70}\n")

    html_path = save_report(rep, Path("storage/outputs"), emit_json=not args.no_json)
    print(f"Report saved: {html_path}")
    sys.exit(0 if rep.verdict==Status.PASS else 1)


if __name__ == "__main__":
    main()
