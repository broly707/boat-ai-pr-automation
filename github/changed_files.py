from git import Repo


def get_pr_changed_files(
    repo_path,
    target_branch,
    source_branch
):

    repo = Repo(repo_path)

    origin = repo.remotes.origin

    origin.fetch()

    try:

        changed_files = repo.git.diff(
            "--name-only",
            f"origin/{target_branch}",
            f"origin/{source_branch}"
        )

        return [
            line.strip()
            for line in changed_files.splitlines()
            if line.strip()
        ]

    except Exception as e:

        print(
            f"PR Changed Files Error: {e}"
        )

        return []


def get_incremental_changed_files(
    repo_path,
    before_sha,
    after_sha
):

    repo = Repo(repo_path)

    try:

        changed_files = repo.git.diff(
            "--name-only",
            before_sha,
            after_sha
        )

        return [
            line.strip()
            for line in changed_files.splitlines()
            if line.strip()
        ]

    except Exception as e:

        print(
            f"Incremental Changed Files Error: {e}"
        )

        return []