import requests

from github.github_auth import (
    generate_installation_token
)


def post_pr_comment(
    repo_name,
    pr_number,
    review
):

    token = (
        generate_installation_token()
    )

    url = (
        f"https://api.github.com/repos/"
        f"{repo_name}/issues/"
        f"{pr_number}/comments"
    )

    headers = {
        "Authorization":
        f"token {token}",

        "Accept":
        "application/vnd.github+json"
    }

    body = {
        "body":
        f"## AI Code Review\n\n{review}"
    }

    response = requests.post(
        url,
        headers=headers,
        json=body
    )

    response.raise_for_status()


def get_pr_details(
    repo_name,
    pr_number
) -> tuple[str, str]:

    try:
        token = generate_installation_token()

        url = (
            f"https://api.github.com/repos/"
            f"{repo_name}/pulls/{pr_number}"
        )

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.get(
            url,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            title = data.get("title") or ""
            body = data.get("body") or ""
            return title, body

    except Exception as e:
        print(f"Error fetching live PR details from GitHub API: {e}")

    return "", ""