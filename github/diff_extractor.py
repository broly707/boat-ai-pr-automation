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
