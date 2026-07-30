import os
import re
from git import Repo

_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php",
    ".swift", ".kt", ".kts", ".rs", ".scala", ".vue"
}

_TODO_FIXME_PATTERN = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
_INLINE_COMMENT_PATTERN = re.compile(r"(?<!:)(?<!\*)//(?!\s*/)(.*)$")
_BLOCK_COMMENT_PATTERN = re.compile(r"/\*+(.*?)\*/", re.DOTALL)


def is_reviewable_file(file_path: str) -> bool:
    _, ext = os.path.splitext(file_path.lower())
    return ext in _CODE_EXTENSIONS


def get_file_content(
    repo_path: str,
    file_ref: str,
    file_path: str
) -> str | None:

    repo = Repo(repo_path)

    try:
        return repo.git.show(f"{file_ref}:{file_path}")
    except Exception as e:
        print(
            f"[COMMENT EXTRACTOR] Could not read {file_path} at {file_ref}: {e}"
        )
        return None


def _is_todo_fixme(comment_text: str) -> bool:
    return bool(_TODO_FIXME_PATTERN.search(comment_text))


def _clean_block_comment(raw_comment: str) -> str:
    cleaned = re.sub(r"^/\*\*?", "", raw_comment.strip())
    cleaned = re.sub(r"\*/$", "", cleaned.strip())
    cleaned = re.sub(r"^\*\s?", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def _get_following_code(
    lines: list[str],
    start_idx: int,
    max_lines: int = 15
) -> str:

    collected = []

    for i in range(start_idx, min(start_idx + max_lines, len(lines))):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if collected:
                break
            continue

        if (
            stripped.startswith("//")
            or stripped.startswith("#")
            or stripped.startswith("/*")
            or stripped.startswith("*")
        ):
            if collected:
                break
            continue

        collected.append(line.rstrip())

    return "\n".join(collected).strip()


def _append_comment(
    comments: list[dict],
    file_path: str,
    line_number: int,
    comment_text: str,
    code_snippet: str
) -> None:

    comment_text = comment_text.strip()

    if not comment_text or _is_todo_fixme(comment_text):
        return

    comments.append(
        {
            "file": file_path,
            "line": str(line_number),
            "comment": comment_text,
            "code": code_snippet or "(no associated code found)"
        }
    )


def extract_comments_from_content(
    content: str,
    file_path: str
) -> list[dict]:

    comments: list[dict] = []
    lines = content.splitlines()
    in_block = False
    block_start_line = 0
    block_lines: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        line_number = idx + 1

        if in_block:
            block_lines.append(line)
            if "*/" in line:
                in_block = False
                raw_block = "\n".join(block_lines)
                comment_text = _clean_block_comment(raw_block)
                code_snippet = _get_following_code(lines, idx + 1)
                _append_comment(
                    comments,
                    file_path,
                    block_start_line,
                    comment_text,
                    code_snippet
                )
                block_lines = []
            idx += 1
            continue

        stripped = line.strip()

        if "/*" in line:
            if "*/" in line:
                for match in _BLOCK_COMMENT_PATTERN.finditer(line):
                    comment_text = _clean_block_comment(match.group(0))
                    code_before = line[:match.start()].strip()
                    code_snippet = code_before or _get_following_code(
                        lines,
                        idx + 1
                    )
                    _append_comment(
                        comments,
                        file_path,
                        line_number,
                        comment_text,
                        code_snippet
                    )
            else:
                in_block = True
                block_start_line = line_number
                block_lines = [line]
            idx += 1
            continue

        if stripped.startswith("//"):
            comment_text = stripped[2:].strip()
            code_snippet = _get_following_code(lines, idx + 1)
            _append_comment(
                comments,
                file_path,
                line_number,
                comment_text,
                code_snippet
            )
            idx += 1
            continue

        if stripped.startswith("#") and not stripped.startswith("#!"):
            comment_text = stripped[1:].strip()
            code_snippet = _get_following_code(lines, idx + 1)
            _append_comment(
                comments,
                file_path,
                line_number,
                comment_text,
                code_snippet
            )
            idx += 1
            continue

        inline_match = _INLINE_COMMENT_PATTERN.search(line)
        if inline_match:
            comment_text = inline_match.group(1).strip()
            code_snippet = line[:inline_match.start()].strip()
            _append_comment(
                comments,
                file_path,
                line_number,
                comment_text,
                code_snippet
            )
            idx += 1
            continue

        docstring_match = re.match(
            r'^\s*(["\']{3})(.*?)\1\s*$',
            line
        )
        if docstring_match:
            comment_text = docstring_match.group(2).strip()
            code_snippet = _get_following_code(lines, idx + 1)
            _append_comment(
                comments,
                file_path,
                line_number,
                comment_text,
                code_snippet
            )
            idx += 1
            continue

        multiline_docstring = False
        for quote in ('"""', "'''"):
            if stripped.startswith(quote) and not stripped.endswith(quote):
                doc_lines = [line]
                end_idx = idx
                for j in range(idx + 1, len(lines)):
                    doc_lines.append(lines[j])
                    end_idx = j
                    if lines[j].strip().endswith(quote):
                        break
                raw_doc = "\n".join(doc_lines)
                comment_text = raw_doc.strip().strip(quote).strip()
                code_snippet = _get_following_code(lines, end_idx + 1)
                _append_comment(
                    comments,
                    file_path,
                    line_number,
                    comment_text,
                    code_snippet
                )
                idx = end_idx + 1
                multiline_docstring = True
                break

        if multiline_docstring:
            continue

        idx += 1

    return comments


def extract_comments_from_files(
    repo_path: str,
    changed_files: list[str],
    source_branch: str,
    after_sha: str | None = None
) -> list[dict]:

    repo = Repo(repo_path)

    if not after_sha:
        try:
            repo.remotes.origin.fetch()
        except Exception as e:
            print(f"[COMMENT EXTRACTOR] Origin fetch warning: {e}")

    file_ref = after_sha if after_sha else f"origin/{source_branch}"
    all_comments: list[dict] = []

    for file_path in changed_files:
        if not is_reviewable_file(file_path):
            continue

        content = get_file_content(repo_path, file_ref, file_path)
        if not content:
            continue

        file_comments = extract_comments_from_content(
            content,
            file_path
        )
        all_comments.extend(file_comments)

    return all_comments
