from git import Repo


def get_diff(
    repo_path,
    target_branch,
    source_branch
):

    repo = Repo(repo_path)

    origin = repo.remotes.origin

    origin.fetch()

    try:

        diff_output = repo.git.diff(
            f"origin/{target_branch}",
            f"origin/{source_branch}"
        )

        return diff_output

    except Exception as e:

        print(
            f"Diff Extraction Error: {e}"
        )

        return ""


def get_incremental_diff(
    repo_path,
    before_sha,
    after_sha
):

    repo = Repo(repo_path)

    try:

        diff_output = repo.git.diff(
            before_sha,
            after_sha
        )

        return diff_output

    except Exception as e:

        print(
            f"Incremental Diff Error: {e}"
        )

        return ""


import re


def extract_added_code(
    diff_text
):
    """
    Extract added code lines from a git diff and prefix every line with its exact
    real line number from the target file.
    """
    extracted_lines = []
    current_file = None
    current_line = 0

    # Pattern for hunk header e.g. @@ -10,6 +12,15 @@
    hunk_pattern = re.compile(
        r"^@@ -\d+(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@"
    )

    for line in diff_text.splitlines():

        if line.startswith(
            "diff --git"
        ):
            try:
                current_file = (
                    line.split(
                        " b/"
                    )[1]
                )
                extracted_lines.append(
                    f"\nFILE: {current_file}\n"
                )
            except Exception:
                pass
            current_line = 0
            continue

        if (
            line.startswith("index ")
            or line.startswith("---")
            or line.startswith("+++")
        ):
            continue

        hunk_match = hunk_pattern.match(line)
        if hunk_match:
            current_line = int(hunk_match.group("new_start"))
            continue

        if current_file is None:
            continue

        if line.startswith("+"):
            content = line[1:]
            extracted_lines.append(
                f"L{current_line}: {content}"
            )
            current_line += 1
        elif line.startswith(" "):
            # Context line in target file: increment line count
            current_line += 1
        elif line.startswith("-"):
            # Deleted line in target file: do not increment target line count
            pass

    return "\n".join(
        extracted_lines
    )


import os


def extract_full_code(
    workspace_path: str,
    changed_files: list
) -> str:
    """
    Reads the complete, unmodified source code for each changed file from the workspace,
    prefixing every line with its exact 1-based line number from the source file.
    Encloses each file in a properly formatted code block.
    """
    file_blocks = []

    for rel_path in changed_files:
        full_path = os.path.join(workspace_path, rel_path)

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines = content.splitlines()
            numbered_lines = [
                f"L{idx}: {line}"
                for idx, line in enumerate(lines, start=1)
            ]
            formatted_code = "\n".join(numbered_lines)

            ext = os.path.splitext(rel_path)[1].lstrip(".")
            lang = ext if ext else "text"

            file_block = (
                f"FILE: {rel_path}\n"
                f"```{lang}\n"
                f"{formatted_code}\n"
                "```"
            )
            file_blocks.append(file_block)

        except Exception as e:
            print(f"[FILE EXTRACTION WARNING] Could not read {rel_path}: {e}")

    if not file_blocks:
        return ""

    return "\n\n".join(file_blocks)


def _normalize_repo_path(path: str) -> str:

    return (path or "").strip().replace("\\", "/").lstrip("./")


def _paths_match(diff_path: str, rel_path: str) -> bool:

    diff_norm = _normalize_repo_path(diff_path)
    rel_norm = _normalize_repo_path(rel_path)

    if not diff_norm or not rel_norm:
        return False

    if diff_norm == rel_norm:
        return True

    return (
        diff_norm.endswith("/" + rel_norm)
        or rel_norm.endswith("/" + diff_norm)
        or diff_norm.endswith(rel_norm)
        or rel_norm.endswith(diff_norm)
    )


def resolve_workspace_file_path(
    workspace_path: str,
    rel_path: str
) -> str | None:

    rel_path = _normalize_repo_path(rel_path)
    if not rel_path or not workspace_path:
        return None

    direct_path = os.path.join(
        workspace_path,
        rel_path.replace("/", os.sep)
    )
    if os.path.isfile(direct_path):
        return direct_path

    basename = os.path.basename(rel_path)
    suffix_matches = []
    basename_matches = []

    for root, dirs, files in os.walk(workspace_path):
        if ".git" in dirs:
            dirs.remove(".git")

        for filename in files:
            full_path = os.path.join(root, filename)
            normalized = full_path.replace("\\", "/")

            if filename == basename:
                basename_matches.append(full_path)

            if normalized.endswith("/" + rel_path) or normalized.endswith(rel_path):
                suffix_matches.append(full_path)

    if len(suffix_matches) == 1:
        return suffix_matches[0]

    if len(suffix_matches) > 1:
        for candidate in suffix_matches:
            if candidate.replace("\\", "/").endswith(rel_path):
                return candidate

    if len(basename_matches) == 1:
        return basename_matches[0]

    return None


def extract_lines_from_diff(
    diff_text: str,
    rel_path: str,
    line_spec: str
) -> str:

    if not diff_text or not rel_path or not line_spec:
        return ""

    parsed = _parse_line_spec(line_spec)
    if not parsed:
        print(
            f"[CODE EXTRACT] Could not parse line spec from diff: {line_spec!r}"
        )
        return ""

    start_line, end_line = parsed
    if start_line > end_line:
        start_line, end_line = end_line, start_line

    hunk_pattern = re.compile(
        r"^@@ -\d+(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@"
    )

    current_file = None
    current_line = 0
    collected: dict[int, str] = {}

    for line in diff_text.splitlines():

        if line.startswith("diff --git"):
            try:
                current_file = line.split(" b/")[1]
            except Exception:
                current_file = None
            current_line = 0
            continue

        if not current_file or not _paths_match(current_file, rel_path):
            continue

        if (
            line.startswith("index ")
            or line.startswith("---")
            or line.startswith("+++")
        ):
            continue

        hunk_match = hunk_pattern.match(line)
        if hunk_match:
            current_line = int(hunk_match.group("new_start"))
            continue

        if line.startswith("+") or line.startswith(" "):
            if start_line <= current_line <= end_line:
                collected[current_line] = line[1:]
            current_line += 1
        elif line.startswith("-"):
            pass

    if not collected:
        print(
            f"[CODE EXTRACT] No diff lines found for {rel_path} {line_spec}"
        )
        return ""

    snippet_lines = [
        collected[line_no]
        for line_no in range(start_line, end_line + 1)
        if line_no in collected
    ]

    return "\n".join(snippet_lines)


def _parse_line_spec(line_spec: str) -> tuple[int, int] | None:

    line_spec = (line_spec or "").strip()
    line_spec = re.sub(
        r"[\u2011\u2013\u2014\u2010]",
        "-",
        line_spec
    )
    line_spec = re.sub(r"\s+", "", line_spec)

    range_match = re.match(
        r"^L?(\d+)\s*-\s*L?(\d+)$",
        line_spec,
        re.IGNORECASE
    )
    if range_match:
        return (
            int(range_match.group(1)),
            int(range_match.group(2))
        )

    single_match = re.match(
        r"^L?(\d+)$",
        line_spec,
        re.IGNORECASE
    )
    if single_match:
        line_no = int(single_match.group(1))
        return line_no, line_no

    return None


def extract_source_lines(
    workspace_path: str,
    rel_path: str,
    line_spec: str
) -> str:

    rel_path = _normalize_repo_path(rel_path)
    if not rel_path or not line_spec:
        return ""

    full_path = resolve_workspace_file_path(
        workspace_path,
        rel_path
    )

    if not full_path:
        print(
            f"[CODE EXTRACT] Source file not found in workspace: {rel_path}"
        )
        return ""

    parsed = _parse_line_spec(line_spec)
    if not parsed:
        print(
            f"[CODE EXTRACT] Could not parse line spec: {line_spec!r}"
        )
        return ""

    start_line, end_line = parsed
    if start_line > end_line:
        start_line, end_line = end_line, start_line

    try:
        with open(
            full_path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as source_file:
            all_lines = source_file.read().splitlines()
    except Exception as err:
        print(
            f"[CODE EXTRACT] Failed to read {rel_path}: {err}"
        )
        return ""

    if start_line < 1 or start_line > len(all_lines):
        return ""

    end_line = min(end_line, len(all_lines))
    snippet_lines = all_lines[start_line - 1:end_line]

    return "\n".join(snippet_lines)


def resolve_code_snippet(
    workspace_path: str | None,
    rel_path: str,
    line_spec: str,
    diff_text: str | None = None
) -> str:

    rel_path = (rel_path or "").strip()
    line_spec = (line_spec or "").strip()

    if not rel_path or not line_spec:
        return ""

    if workspace_path:
        extracted = extract_source_lines(
            workspace_path,
            rel_path,
            line_spec
        )
        if extracted:
            print(
                f"[CODE EXTRACT] Resolved snippet from source file: "
                f"{rel_path} {line_spec}"
            )
            return extracted

    if diff_text:
        extracted = extract_lines_from_diff(
            diff_text,
            rel_path,
            line_spec
        )
        if extracted:
            print(
                f"[CODE EXTRACT] Resolved snippet from git diff: "
                f"{rel_path} {line_spec}"
            )
            return extracted

    return ""

