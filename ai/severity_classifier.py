"""
severity_classifier.py

Classifies AI Code Review issues into severity categories:
🔴 High
🟠 Moderate
🟢 Low

Groups the original issue blocks under the corresponding severity headings
without modifying the issue content, wording, or structure.
"""

import re


def classify_issue_severity(issue_block: str) -> str:
    """
    Classify an issue block into 'High', 'Moderate', or 'Low' severity.
    """
    text_lower = issue_block.lower()

    # High severity: Critical bugs, crash risks, null pointer exceptions,
    # security vulnerabilities, memory leaks, undefined variables, data loss.
    high_keywords = [
        "crash", "nullpointer", "null pointer", "npe", "security", "vulnerability",
        "memory leak", "data loss", "deadlock", "race condition", "undefined variable",
        "syntax error", "fatal", "unhandled exception", "arrayindexoutofbounds",
        "indexoutofbounds", "classcast", "typeerror", "stackoverflow", "infinite loop"
    ]

    # Low severity: Code style, formatting, unused imports, typos, documentation.
    low_keywords = [
        "unused import", "formatting", "indentation", "style", "naming convention",
        "typo", "spelling", "kdoc", "javadoc", "documentation comment"
    ]

    for kw in high_keywords:
        if kw in text_lower:
            return "High"

    for kw in low_keywords:
        if kw in text_lower:
            return "Low"

    # Default: Moderate severity for general logic, resources, UI/view issues,
    # unused methods, missing error handling, etc.
    return "Moderate"


def classify_and_group_review(review_text: str) -> str:
    """
    Parses issue blocks from the raw review text, classifies each block by severity,
    and returns the review text with issues grouped under severity headings:
    - ### 🔴 High Severity
    - ### 🟠 Moderate Severity
    - ### 🟢 Low Severity

    If no issue blocks are found, returns the review text as-is.
    """
    if not review_text or "Issue:" not in review_text:
        return review_text

    # Split into preamble and issue blocks.
    # We split on occurrences of 'Issue:' (case-insensitive) using regex lookahead/split.
    raw_blocks = re.split(r"(?=\n?\s*Issue\s*:)", review_text, flags=re.IGNORECASE)

    preamble = ""
    issue_blocks = []

    for block in raw_blocks:
        block_str = block.strip()
        if not block_str:
            continue

        if re.match(r"^Issue\s*:", block_str, re.IGNORECASE):
            issue_blocks.append(block_str)
        else:
            if not preamble:
                preamble = block_str

    if not issue_blocks:
        return review_text

    # Categorize issue blocks
    high_issues = []
    moderate_issues = []
    low_issues = []

    for block in issue_blocks:
        severity = classify_issue_severity(block)
        if severity == "High":
            high_issues.append(block)
        elif severity == "Low":
            low_issues.append(block)
        else:
            moderate_issues.append(block)

    # Build output sections
    sections = []

    if preamble and not preamble.lower().startswith("here are the issues"):
        sections.append(preamble)

    if high_issues:
        sections.append("### 🔴 High Severity\n\n" + "\n\n".join(high_issues))

    if moderate_issues:
        sections.append("### 🟠 Moderate Severity\n\n" + "\n\n".join(moderate_issues))

    if low_issues:
        sections.append("### 🟢 Low Severity\n\n" + "\n\n".join(low_issues))

    return "\n\n".join(sections)
