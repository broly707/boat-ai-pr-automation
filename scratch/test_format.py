import sys
sys.path.insert(0, ".")

import re
from ai.severity_classifier import _detect_language

def format_issue_block(block: str) -> str:
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

        if field_name in fields:
            continue

        start_val = match.end()
        end_val = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        val = block[start_val:end_val]
        fields[field_name] = val

    header_lines = []

    if "Issue" in fields:
        header_lines.append(f"Issue: {fields['Issue'].strip()}")

    file_val = fields.get("File", "").strip()
    if file_val:
        header_lines.append(f"File: {file_val}")

    if "Line" in fields:
        line_val = fields["Line"].strip()
        if line_val:
            header_lines.append(f"Line: {line_val}")

    header_lines.append("Code:")

    lang = _detect_language(file_val)

    code_raw = fields.get("Code", "")
    if code_raw.startswith(" "):
        code_raw = code_raw[1:]
    code_raw = code_raw.strip("\r\n")

    backtick_match = re.match(r"^```(\w*)\n?(.*?)\n?```\s*$", code_raw, re.DOTALL)
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

    reason_val = fields.get("Reason", "").strip()
    sug_val = fields.get("Suggestion", "").strip()

    footer_lines = []
    if reason_val:
        footer_lines.append(f"Reason: {reason_val}")
    if sug_val:
        footer_lines.append(f"Suggestion: {sug_val}")

    parts = ["\n".join(header_lines)]
    parts.append(formatted_code_block)
    if footer_lines:
        parts.append("\n".join(footer_lines))

    return "\n\n".join(parts)


sample_block = "\n".join([
    "Issue: Missing error handling",
    "File: app/src/main/java/com/example/practice/MainActivity.kt",
    "Line: 49-53, 64-68",
    "Code:",
    "Toast.makeText(",
    "    this,",
    "    getString(R.string.msg_counter_incremented),",
    "    Toast.LENGTH_SHORT",
    ").show()",
    "",
    "Reason: If the string resources are missing, the app will crash.",
    "Suggestion: Add error handling to ensure the app does not crash if the string resources are missing.",
    "",
    "Code:",
    "N/A"
])

print(format_issue_block(sample_block))
