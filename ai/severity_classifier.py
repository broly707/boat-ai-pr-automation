"""
severity_classifier.py

Classifies AI Code Review issues into severity categories:
🔴 High
🟠 Moderate
🟢 Low

Groups the original issue blocks under the corresponding severity headings
without modifying the issue content, wording, or structure.
Cleans up duplicate issues and self-corrected / invalidated false positives.
"""

import re

INVALIDATION_PATTERNS = [
    r"upon\s+closer\s+inspection",
    r"however,?\s+upon\s+closer",
    r"is\s+not\s+actually\s+(?:an?\s+)?issue",
    r"the\s+issue\s+is\s+not\s+with",
    r"the\s+issue\s+is\s+actually\s+with",
    r"is\s+actually\s+being\s+used",
    r"is\s+actually\s+in\s+the\s+companion\s+object",
    r"is\s+accessible\s+in\s+the\s+same\s+scope",
    r"is\s+not\s+necessary\s+in\s+this\s+case",
    r"disregard",
    r"false\s+positive",
    r"no\s+issue\s+here",
    r"correction\s*:",
    r"the\s+only\s+actual\s+issues?\s+found",
    r"upon\s+closer\s+examination",
    r"not\s+an\s+issue",
    r"is\s+actually\s+correct",
]


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


def _detect_language(file_path: str) -> str:
    if not file_path:
        return "text"
    file_path = file_path.strip().lower()
    ext_map = {
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".java": "java",
        ".xml": "xml",
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".swift": "swift",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".gradle": "groovy",
        ".properties": "properties",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".md": "markdown",
    }
    for ext, lang in ext_map.items():
        if file_path.endswith(ext):
            return lang
    return "text"


def format_issue_block(block: str) -> str:
    """
    Formats a single issue block to enforce strict Code section formatting rules:
    - Code: is on its own line
    - Followed by a blank line
    - Followed by fenced Markdown code block with language syntax highlighting
    - If empty or 'N/A', displays ```text\nN/A\n``` after blank line.
    - Fields: Issue, File, Line, Code, Reason, Suggestion
    """
    if not block or not re.search(r"Issue\s*:", block, re.IGNORECASE):
        return block

    headers_pattern = re.compile(
        r"(?:^|\n)\s*(Issue|File|Line|Code|Reason|Suggestion)\s*:",
        re.IGNORECASE
    )

    matches = list(headers_pattern.finditer(block))
    if not matches:
        return block

    fields = {}

    for i, match in enumerate(matches):
        raw_name = match.group(1).lower()
        if raw_name == "issue":
            field_name = "Issue"
        elif raw_name == "file":
            field_name = "File"
        elif raw_name == "line":
            field_name = "Line"
        elif raw_name == "code":
            field_name = "Code"
        elif raw_name == "reason":
            field_name = "Reason"
        elif raw_name == "suggestion":
            field_name = "Suggestion"
        else:
            field_name = raw_name.capitalize()

        start_val = match.end()
        end_val = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        val = block[start_val:end_val]

        fields[field_name] = val

    parts = []

    file_val = fields.get("File", "").strip()
    lang = _detect_language(file_val)

    if "Issue" in fields:
        parts.append(f"Issue: {fields['Issue'].strip()}")

    if file_val:
        parts.append(f"File: {file_val}")

    if "Line" in fields:
        line_val = fields["Line"].strip()
        if line_val:
            parts.append(f"Line: {line_val}")

    code_raw = fields.get("Code", "")
    if code_raw.startswith(" "):
        code_raw = code_raw[1:]
    code_raw = code_raw.strip("\r\n")

    # If code_raw is already wrapped in backticks, extract inner content and language
    backtick_match = re.match(r"^```(\w*)\n?(.*)\n?```$", code_raw, re.DOTALL)
    if backtick_match:
        extracted_lang = backtick_match.group(1).strip()
        if extracted_lang:
            lang = extracted_lang
        code_raw = backtick_match.group(2).strip("\r\n")

    code_lines = code_raw.splitlines() if code_raw else []

    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()

    cleaned_code = "\n".join(code_lines) if code_lines else ""

    if not cleaned_code or cleaned_code.strip().upper() == "N/A":
        formatted_code_block = "```text\nN/A\n```"
    else:
        formatted_code_block = f"```{lang}\n{cleaned_code}\n```"

    parts.append(f"\nCode:\n\n{formatted_code_block}")

    if "Reason" in fields:
        reason_val = fields["Reason"].strip()
        if reason_val:
            parts.append(f"\nReason: {reason_val}")

    if "Suggestion" in fields:
        sug_val = fields["Suggestion"].strip()
        if sug_val:
            parts.append(f"\nSuggestion: {sug_val}")

    return "\n".join(parts)


def _clean_issue_block(block: str) -> str | None:
    """
    Cleans an issue block. Returns None if the issue was invalidated or false-positive.
    Also discards issues with no supporting code evidence (empty or N/A Code field).
    """
    if not block or not re.match(r"^Issue\s*:", block.strip(), re.IGNORECASE):
        return None

    # Check for invalidation keywords anywhere in the block
    for pattern in INVALIDATION_PATTERNS:
        if re.search(pattern, block, re.IGNORECASE):
            return None

    # Trim block to end at Suggestion field if present, or end of known fields
    suggestion_match = re.search(
        r"(Suggestion\s*:\s*.+?)(?=\n\n|\n[A-Z][a-z]+:|\Z)",
        block,
        re.DOTALL | re.IGNORECASE
    )
    if suggestion_match:
        end_pos = suggestion_match.end()
        clean_text = block[:end_pos].strip()
    else:
        # Otherwise trim trailing meta phrases
        clean_text = re.sub(
            r"\n\s*(?:However|The only actual|Upon closer|Correction|Disregard).*",
            "",
            block,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()

    if not clean_text:
        return None

    # Evidence guard: discard issues whose Code field is empty or N/A.
    # These have no supporting code and are therefore false positives.
    code_match = re.search(
        r"Code\s*:\s*(.*?)(?=\n\s*(?:Reason|Suggestion)\s*:|\Z)",
        clean_text,
        re.DOTALL | re.IGNORECASE
    )
    if code_match:
        raw_code = code_match.group(1).strip()
        # Strip fenced code block markers to get inner content
        inner = re.sub(r"^```\w*\n?", "", raw_code, flags=re.IGNORECASE)
        inner = re.sub(r"\n?```\s*$", "", inner, flags=re.IGNORECASE)
        inner = inner.strip()
        if not inner or inner.upper() == "N/A":
            print(
                f"[EVIDENCE FILTER] Discarding issue with no code evidence: "
                f"{re.search(r'Issue\\s*:\\s*(.+?)(?=\\n|$)', clean_text, re.IGNORECASE).group(1).strip() if re.search(r'Issue\\s*:\\s*(.+?)(?=\\n|$)', clean_text, re.IGNORECASE) else '(unknown)'}"
            )
            return None

    return format_issue_block(clean_text)


def _compute_issue_key(block: str) -> str:
    """
    Computes a normalized key for deduplication based on Issue title, File, Line, and Code.
    """
    issue_match = re.search(r"Issue\s*:\s*(.+?)(?=\n|$)", block, re.IGNORECASE)
    file_match = re.search(r"File\s*:\s*(.+?)(?=\n|$)", block, re.IGNORECASE)
    line_match = re.search(r"Line\s*:\s*(.+?)(?=\n|$)", block, re.IGNORECASE)
    code_match = re.search(
        r"Code\s*:\s*(.+?)(?=\n\s*(?:Reason|Suggestion)\s*:|$)",
        block,
        re.DOTALL | re.IGNORECASE
    )

    issue_str = issue_match.group(1).strip().lower() if issue_match else ""
    file_str = file_match.group(1).strip().lower() if file_match else ""
    line_str = line_match.group(1).strip().lower() if line_match else ""
    code_str = code_match.group(1).strip().lower() if code_match else ""

    issue_str = re.sub(r"\s+", " ", issue_str)
    file_str = re.sub(r"\s+", " ", file_str)
    line_str = re.sub(r"\s+", " ", line_str)
    code_str = re.sub(r"\s+", " ", code_str)

    if issue_str and (file_str or code_str):
        return f"{issue_str}|{file_str}|{line_str}|{code_str}"

    return re.sub(r"\s+", " ", block.lower())


def classify_and_group_review(review_text: str) -> str:
    """
    Parses issue blocks from the raw review text, filters out invalidated/false-positive
    issues, deduplicates identical issues, classifies each block by severity,
    and returns the review text with issues grouped under severity headings:
    - ### 🔴 High Severity
    - ### 🟠 Moderate Severity
    - ### 🟢 Low Severity

    If no issue blocks are found, returns the review text as-is.
    """
    if not review_text or "Issue:" not in review_text:
        return review_text

    # Check if there is a late summary section like "The only actual issues found in the provided code are:"
    # If so, prefer issue blocks after the last occurrence of such summary marker.
    summary_marker_match = list(re.finditer(
        r"the\s+only\s+actual\s+issues?\s+found.*?:",
        review_text,
        re.IGNORECASE
    ))
    if summary_marker_match:
        last_marker = summary_marker_match[-1]
        after_text = review_text[last_marker.end():].strip()
        if "Issue:" in after_text:
            review_text = after_text

    # Split into preamble and issue blocks.
    raw_blocks = re.split(r"(?=\n?\s*Issue\s*:)", review_text, flags=re.IGNORECASE)

    preamble = ""
    issue_blocks = []
    seen_keys = set()

    for block in raw_blocks:
        block_str = block.strip()
        if not block_str:
            continue

        if re.match(r"^Issue\s*:", block_str, re.IGNORECASE):
            cleaned_block = _clean_issue_block(block_str)
            if cleaned_block:
                key = _compute_issue_key(cleaned_block)
                if key not in seen_keys:
                    seen_keys.add(key)
                    issue_blocks.append(cleaned_block)
        else:
            if not preamble and not re.search(r"the\s+only\s+actual\s+issues?", block_str, re.IGNORECASE):
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

    if preamble and not preamble.lower().startswith("here are the issues") and not preamble.lower().startswith("the only actual"):
        sections.append(preamble)

    if high_issues:
        sections.append("### 🔴 High Severity\n\n" + "\n\n".join(high_issues))

    if moderate_issues:
        sections.append("### 🟠 Moderate Severity\n\n" + "\n\n".join(moderate_issues))

    if low_issues:
        sections.append("### 🟢 Low Severity\n\n" + "\n\n".join(low_issues))

    return "\n\n".join(sections)

