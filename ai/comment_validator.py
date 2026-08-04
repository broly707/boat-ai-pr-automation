import os
import re
from groq import Groq

from github.comment_extractor import extract_comments_from_files

_MISMATCH_BLOCK_PATTERN = re.compile(
    r"File:\s*(?P<file>.+?)\s*\n"
    r"Line:\s*(?P<line>.+?)\s*\n"
    r'Comment:\s*"(?P<comment>.+?)"\s*\n'
    r"Code:\s*(?P<code>.+?)\s*\n"
    r"Reason:\s*(?P<reason>.+?)(?=\n---|\nFile:|\Z)",
    re.DOTALL | re.IGNORECASE
)


def _build_file_validation_prompt(file_path: str, comments: list[dict]) -> str:
    comment_blocks = []

    for index, item in enumerate(comments, start=1):
        comment_blocks.append(
            f"Comment {index}:\n"
            f"Line: {item['line']}\n"
            f"Comment: \"{item['comment']}\"\n"
            f"Associated Code:\n{item['code']}\n"
        )

    joined_comments = "\n".join(comment_blocks)

    return f"""You are a strict code comment accuracy validator.

File: {file_path}

Review each comment below against the associated code that follows or sits beside it.

Flag a mismatch ONLY when:
- The comment describes behavior the code does not perform.
- The comment describes a calculation, condition, or return value that differs from the implementation.
- A @param or @return doc tag does not match actual parameters, return type, or behavior.
- The comment is outdated relative to the current code beneath it.

Do NOT flag:
- Minor wording or style differences that do not change the meaning.
- Comments that are accurate but less detailed than the code.
- TODO/FIXME comments (already excluded).

Comments to review:
{joined_comments}

If you find one or more mismatches, respond using one block per mismatch in exactly this format:
---
File: {file_path}
Line: <line number(s)>
Comment: "<exact comment text>"
Code: <short snippet or summary of what the code actually does>
Reason: <clear, specific explanation of the mismatch>
---

If every comment accurately matches the code, respond with exactly:
NO_MISMATCHES
"""


def _parse_mismatch_blocks(response_text: str) -> list[dict]:
    mismatches = []

    for match in _MISMATCH_BLOCK_PATTERN.finditer(response_text):
        mismatches.append(
            {
                "file": match.group("file").strip(),
                "line": match.group("line").strip(),
                "comment": match.group("comment").strip(),
                "code": " ".join(
                    match.group("code").strip().splitlines()
                ),
                "reason": match.group("reason").strip()
            }
        )

    return mismatches


def _validate_file_comments(
    client: Groq,
    file_path: str,
    comments: list[dict]
) -> list[dict]:

    prompt = _build_file_validation_prompt(file_path, comments)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0,
        max_tokens=2048,
        top_p=1,
        stream=False
    )

    response_text = (
        completion.choices[0].message.content or ""
    ).strip()

    print("\n===== COMMENT VALIDATION LLM RESPONSE =====")
    print(f"File: {file_path}")
    print(response_text)
    print("===========================================\n")

    if "NO_MISMATCHES" in response_text.upper():
        return []

    return _parse_mismatch_blocks(response_text)


def validate_code_comments(
    repo_path: str,
    changed_files: list[str],
    source_branch: str,
    after_sha: str | None = None
) -> list[dict]:

    print("\n===== CODE COMMENT VALIDATION GATE =====")

    comments = extract_comments_from_files(
        repo_path,
        changed_files,
        source_branch,
        after_sha
    )

    if not comments:
        print("No reviewable comments found in changed files. Skipping gate.")
        return []

    print(f"Found {len(comments)} comment(s) to validate across changed files.")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print(
            "[WARNING] GROQ_API_KEY not found. "
            "Skipping comment validation gate."
        )
        return []

    comments_by_file: dict[str, list[dict]] = {}
    for item in comments:
        comments_by_file.setdefault(item["file"], []).append(item)

    client = Groq(api_key=api_key)
    all_mismatches: list[dict] = []

    try:
        for file_path, file_comments in comments_by_file.items():
            mismatches = _validate_file_comments(
                client,
                file_path,
                file_comments
            )
            all_mismatches.extend(mismatches)
    except Exception as e:
        print(
            f"[WARNING] Comment validation error: {e}. "
            "Allowing review to continue."
        )
        return []

    if all_mismatches:
        print(
            f"Comment Validation Result: FAIL ({len(all_mismatches)} mismatch(es))"
        )
    else:
        print("Comment Validation Result: PASS")

    return all_mismatches


def _build_suggestions(mismatches: list[dict]) -> str:
    """
    Generate actionable suggestions for each mismatch and a general tips section.
    The suggestions are derived from the mismatch reason text so that they are
    specific to the actual problem found in the code.
    """
    suggestion_lines = []

    for index, item in enumerate(mismatches, start=1):
        reason_lower = item["reason"].lower()
        file_ref = f"`{item['file']}` (line {item['line']})"

        # Determine the most relevant suggestion based on the reason text.
        if any(kw in reason_lower for kw in ("param", "@param", "parameter")):
            suggestion = (
                f"Update the `@param` doc tag in {file_ref} to match the actual "
                "parameter name(s), type(s), and description used in the implementation."
            )
        elif any(kw in reason_lower for kw in ("return", "@return", "returns")):
            suggestion = (
                f"Fix the `@return`/`@returns` doc tag in {file_ref} to accurately "
                "reflect the value, type, or condition that the function actually returns."
            )
        elif any(kw in reason_lower for kw in ("outdated", "old", "stale", "no longer")):
            suggestion = (
                f"The comment in {file_ref} appears to describe an older version of the "
                "code. Update it to reflect the current implementation, or remove it if "
                "it is no longer relevant."
            )
        elif any(kw in reason_lower for kw in ("condition", "if", "else", "branch", "check")):
            suggestion = (
                f"Correct the comment in {file_ref} to describe the actual condition or "
                "branch logic. Make sure any referenced variables, operators, or thresholds "
                "match what the code uses."
            )
        elif any(kw in reason_lower for kw in ("calculation", "formula", "compute", "math", "arithmetic")):
            suggestion = (
                f"Update the comment in {file_ref} to reflect the correct formula or "
                "calculation. Double-check the operators and operands described against "
                "the code."
            )
        elif any(kw in reason_lower for kw in ("behavior", "does not perform", "not perform")):
            suggestion = (
                f"Rewrite the comment in {file_ref} to accurately describe what the code "
                "actually does. Remove or correct any references to behavior that is not "
                "present in the implementation."
            )
        else:
            # Generic fallback suggestion.
            suggestion = (
                f"Review the comment in {file_ref} and update it so that it precisely "
                "describes the surrounding code. If the code is correct, fix the comment; "
                "if the comment is the source of truth, fix the code."
            )

        suggestion_lines.append(f"{index}. {suggestion}")

    per_mismatch_block = "\n".join(suggestion_lines)

    general_tips = (
        "**General tips to avoid comment mismatches:**\n"
        "- Keep comments co-located with the code they describe and update them whenever "
        "the code changes.\n"
        "- Prefer self-documenting code for simple logic; add comments only when the "
        "**why** (not the **what**) needs explaining.\n"
        "- For doc-comments (`@param`, `@return`, etc.), regenerate or review them after "
        "every signature change.\n"
        "- Run a quick diff of comments vs. code before pushing to catch stale descriptions early."
    )

    return (
        "**Suggestions to fix the mismatches:**\n\n"
        f"{per_mismatch_block}\n\n"
        f"{general_tips}"
    )


def format_comment_validation_failure(mismatches: list[dict]) -> str:
    blocks = []

    for item in mismatches:
        blocks.append(
            f"File: {item['file']}\n"
            f"Line: {item['line']}\n"
            f"Comment: \"{item['comment']}\"\n"
            f"Code: {item['code']}\n"
            f"Reason: {item['reason']}"
        )

    mismatch_text = "\n\n".join(blocks)

    suggestions = _build_suggestions(mismatches)

    return (
        "\u274c\n\n"
        "Comment Validation Failed\n\n"
        f"{mismatch_text}\n\n"
        "Please update the code comment (or fix the code logic) so they match, "
        "then push a new commit to re-trigger the review.\n\n"
        f"{suggestions}"
    )
