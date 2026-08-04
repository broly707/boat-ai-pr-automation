"""
report_generator.py

Generates a downloadable Microsoft Word (.docx) report from the AI review
results for a given Pull Request.

Public API
----------
parse_review_issues(review_text) -> list[dict]
    Parses the raw AI review string into a list of structured issue dicts.

generate_word_report(repo_name, pr_number, review_text, report_dir) -> str
    Builds the .docx file and returns its absolute path on disk.
"""

import os
import re
import datetime

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Pattern that matches a single issue block as produced by prompt_builder.py:
#   Issue: <text>
#   Code:  <snippet>
#   Reason: <text>
#   Suggestion: <text>
_ISSUE_BLOCK_PATTERN = re.compile(
    r"Issue\s*:\s*(?P<issue>.+?)(?=\nIssue\s*:|\Z)",
    re.DOTALL | re.IGNORECASE
)

# Within an issue block, try to pick up a Code: line as a file/line hint.
_CODE_LINE_PATTERN = re.compile(
    r"Code\s*:\s*(?P<code>[^\n]+)",
    re.IGNORECASE
)

# Attempt to strip Reason/Suggestion trailing lines from the issue text.
_TRAILING_FIELDS_PATTERN = re.compile(
    r"\n(?:Code|Reason|Suggestion)\s*:.*",
    re.DOTALL | re.IGNORECASE
)

# Horizontal rule text used inside the .docx
_SEPARATOR = "\u2500" * 40


# ---------------------------------------------------------------------------
# Public: parse_review_issues
# ---------------------------------------------------------------------------

def parse_review_issues(review_text: str) -> list[dict]:
    """
    Parse the raw AI review text into a list of issue dicts.

    Each dict has the keys:
        file  (str) – file/line hint extracted from the Code: field, or ""
        line  (str) – line reference extracted from the Code: field, or ""
        issue (str) – the cleaned issue description text

    If the structured pattern is not found, falls back to splitting on
    numbered list markers (e.g. "1.", "2.") so the report is never empty
    when the AI produced free-form output.
    """
    issues = []

    blocks = _ISSUE_BLOCK_PATTERN.findall(review_text)

    if blocks:
        for raw_block in blocks:
            raw_block = raw_block.strip()

            # Extract code hint before stripping trailing fields.
            code_match = _CODE_LINE_PATTERN.search(raw_block)
            code_hint = code_match.group("code").strip() if code_match else ""

            # Strip Code/Reason/Suggestion lines from the issue text.
            issue_text = _TRAILING_FIELDS_PATTERN.sub("", raw_block).strip()
            issue_text = re.sub(r"\s+", " ", issue_text).strip()

            if not issue_text:
                continue

            # Try to split file path and line number from the code hint.
            file_hint, line_hint = _extract_file_and_line(code_hint)

            issues.append({
                "file": file_hint,
                "line": line_hint,
                "issue": issue_text,
            })

    else:
        # Fallback: numbered list items.
        fallback_blocks = re.split(
            r"\n\s*\d+[\.\)]\s+",
            review_text.strip()
        )
        for idx, block in enumerate(fallback_blocks):
            block = block.strip()
            if not block:
                continue
            issues.append({
                "file": "",
                "line": "",
                "issue": block,
            })

    return issues


def _extract_file_and_line(code_hint: str) -> tuple[str, str]:
    """
    Attempt to extract a file path and line number from a code snippet hint.

    Handles patterns like:
        src/utils.py:42  ->  file="src/utils.py", line="42"
        utils.py line 10 ->  file="utils.py",     line="10"
        src/utils.py     ->  file="src/utils.py", line=""
    """
    if not code_hint:
        return "", ""

    # Pattern: path/to/file.py:42
    match = re.match(
        r"^(?P<path>[^\s:]+\.\w+)\s*:\s*(?P<line>\d+)",
        code_hint
    )
    if match:
        return match.group("path"), match.group("line")

    # Pattern: path/to/file.py line 42
    match = re.match(
        r"^(?P<path>[^\s]+\.\w+)\s+line\s+(?P<line>\d+)",
        code_hint,
        re.IGNORECASE
    )
    if match:
        return match.group("path"), match.group("line")

    # Pattern: bare file path with a known extension
    match = re.match(
        r"^(?P<path>[^\s]+\.(?:py|js|ts|tsx|jsx|java|go|cs|rb|php|swift|kt|rs))",
        code_hint,
        re.IGNORECASE
    )
    if match:
        return match.group("path"), ""

    return "", ""


# ---------------------------------------------------------------------------
# Public: generate_word_report
# ---------------------------------------------------------------------------

def generate_word_report(
    repo_name: str,
    pr_number: int,
    review_text: str,
    report_dir: str
) -> str:
    """
    Generate a .docx report containing only the AI review issues.

    Parameters
    ----------
    repo_name   : Full repository name, e.g. "org/repo"
    pr_number   : Pull Request number
    review_text : Raw AI review string returned by review_code()
    report_dir  : Directory to save the report in (created if absent)

    Returns
    -------
    Absolute path to the generated .docx file.
    """
    os.makedirs(report_dir, exist_ok=True)

    issues = parse_review_issues(review_text)
    review_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Build a safe filename slug from the repo name.
    repo_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_name)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"pr_{repo_slug}_{pr_number}_{timestamp}.docx"
    file_path = os.path.join(report_dir, filename)

    doc = _build_document(repo_name, pr_number, review_date, issues)
    doc.save(file_path)

    print(f"[REPORT] Word report saved: {file_path}")
    return file_path


# ---------------------------------------------------------------------------
# Internal: document builder
# ---------------------------------------------------------------------------

def _build_document(
    repo_name: str,
    pr_number: int,
    review_date: str,
    issues: list[dict]
) -> Document:
    """Build and return the python-docx Document object."""
    doc = Document()

    # ----- Document title -----
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run("AI Pull Request Review Report")
    title_run.bold = True
    title_run.font.size = Pt(16)
    title_run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)  # dark blue

    doc.add_paragraph()  # spacer

    # ----- Metadata block -----
    _add_meta_line(doc, "Repository", repo_name)
    _add_meta_line(doc, "Pull Request", f"#{pr_number}")
    _add_meta_line(doc, "Review Date", review_date)

    doc.add_paragraph()  # spacer

    # ----- Issues -----
    if not issues:
        _add_separator(doc)
        no_issue_para = doc.add_paragraph()
        no_issue_run = no_issue_para.add_run(
            "No issues were detected in this Pull Request."
        )
        no_issue_run.italic = True
        _add_separator(doc)
    else:
        for idx, item in enumerate(issues, start=1):
            _add_separator(doc)

            # Issue heading
            heading_para = doc.add_paragraph()
            heading_run = heading_para.add_run(f"Issue {idx}")
            heading_run.bold = True
            heading_run.font.size = Pt(12)

            # File
            _add_issue_field(
                doc,
                "File",
                item["file"] if item["file"] else "N/A"
            )

            # Line
            _add_issue_field(
                doc,
                "Line",
                item["line"] if item["line"] else "N/A"
            )

            # Issue description
            _add_issue_field(doc, "Issue", item["issue"])

        _add_separator(doc)

    # ----- Footer: total issues -----
    doc.add_paragraph()  # spacer
    footer_para = doc.add_paragraph()
    footer_run = footer_para.add_run(f"Total Issues: {len(issues)}")
    footer_run.bold = True
    footer_run.font.size = Pt(11)

    return doc


def _add_meta_line(doc: Document, label: str, value: str) -> None:
    """Add a bold-label + normal-value line to the document."""
    para = doc.add_paragraph()
    label_run = para.add_run(f"{label}: ")
    label_run.bold = True
    para.add_run(value)


def _add_separator(doc: Document) -> None:
    """Add a horizontal separator paragraph."""
    sep_para = doc.add_paragraph(_SEPARATOR)
    sep_para.runs[0].font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)


def _add_issue_field(doc: Document, label: str, value: str) -> None:
    """Add a 'Label: value' line inside an issue block."""
    para = doc.add_paragraph()
    label_run = para.add_run(f"{label}: ")
    label_run.bold = True
    para.add_run(value)
