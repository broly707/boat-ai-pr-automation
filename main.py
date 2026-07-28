import json
import hmac
import hashlib
from fastapi import FastAPI, Request

from github.repository_manager import clone_repository
from github.diff_extractor import (
    get_diff,
    get_incremental_diff,
    extract_added_code
)

from github.changed_files import (
    get_pr_changed_files,
    get_incremental_changed_files
)

from github.pr_commenter import post_pr_comment

from ai.prompt_builder import build_review_prompt
from ai.reviewer import review_code

app = FastAPI()

GITHUB_SECRET = "8vR#2mL!Q9xP@7tN$5kZ&4cH^1wJ*6Fy"


def verify_signature(
    payload_body: bytes,
    signature_header: str
) -> bool:

    if not signature_header:
        return False

    try:

        sha_name, signature = (
            signature_header.split("=")
        )

        if sha_name != "sha256":
            return False

        mac = hmac.new(
            GITHUB_SECRET.encode(),
            msg=payload_body,
            digestmod=hashlib.sha256
        )

        expected_signature = (
            mac.hexdigest()
        )

        return hmac.compare_digest(
            expected_signature,
            signature
        )

    except Exception as e:

        print(
            f"Signature Error: {e}"
        )

        return False


@app.get("/")
def home():

    return {
        "message": "AI Code Reviewer V2 Running"
    }


@app.post("/github/webhook")
async def github_webhook(
    request: Request
):

    body = await request.body()

    signature = request.headers.get(
        "X-Hub-Signature-256"
    )

    validation_result = verify_signature(
        body,
        signature
    )

    print("\n================================================")
    print("Webhook Received")
    print("Signature Valid:", validation_result)

    if not validation_result:

        print("Webhook Signature Failed")

        return {
            "status": "error",
            "message": "Invalid signature"
        }

    payload = json.loads(
        body.decode("utf-8")
    )

    event = request.headers.get(
        "X-GitHub-Event"
    )

    action = payload.get(
        "action"
    )

    before_sha = payload.get(
        "before"
    )

    after_sha = payload.get(
        "after"
    )

    print(
        f"Event: {event} | Action: {action}"
    )

    print(
        f"Commit Window Shas -> Before: {before_sha} | After: {after_sha}"
    )

    if event == "ping":

        print(
            "GitHub App webhook verified"
        )

        return {
            "status": "success",
            "message": "pong"
        }

    if event == "pull_request":

        pr = payload.get(
            "pull_request",
            {}
        )

        repo = payload.get(
            "repository",
            {}
        )

        repo_name = repo.get(
            "full_name"
        )

        pr_number = pr.get(
            "number"
        )

        source_branch = pr.get(
            "head",
            {}
        ).get(
            "ref"
        )

        target_branch = pr.get(
            "base",
            {}
        ).get(
            "ref"
        )

        print("\n----- PR DETAILS -----")

        print(
            f"Repository: {repo_name} | PR #{pr_number}"
        )

        print(
            f"Branch Target Route: [{target_branch}] <- [{source_branch}]"
        )

        if action in [
            "opened",
            "synchronize",
            "reopened"
        ]:

            workspace_path = (
                f"workspace/pr_{pr_number}"
            )

            print(
                "\nStarting Repository Clone..."
            )

            workspace_path = clone_repository(
                repo_name,
                workspace_path
            )

            print(
                "Repository Clone Completed"
            )

            print(
                "\nStarting Diff Extraction..."
            )

            if action == "opened":

                print(
                    "Review Type: FULL PR REVIEW"
                )

                diff = get_diff(
                    workspace_path,
                    target_branch,
                    source_branch
                )

            elif (
                action == "synchronize"
                and before_sha
                and after_sha
            ):

                print(
                    "Review Type: INCREMENTAL REVIEW"
                )

                diff = get_incremental_diff(
                    workspace_path,
                    before_sha,
                    after_sha
                )

            else:

                print(
                    "Review Type: FALLBACK FULL REVIEW"
                )

                diff = get_diff(
                    workspace_path,
                    target_branch,
                    source_branch
                )

            print("\n===== PR DIFF =====")
            print(diff)
            print("===================\n")

            if (
                action == "synchronize"
                and before_sha
                and after_sha
            ):

                changed_files = (
                    get_incremental_changed_files(
                        workspace_path,
                        before_sha,
                        after_sha
                    )
                )

            else:

                changed_files = (
                    get_pr_changed_files(
                        workspace_path,
                        target_branch,
                        source_branch
                    )
                )

            print(
                "===== CHANGED FILES ====="
            )

            for file in changed_files:
                print(file)

            print(
                "========================="
            )

            print(
                f"\nSuccessfully Parsed {len(changed_files)} Changed File(s)"
            )

            print(
                "Starting Local AI LLM Processing Engine..."
            )

            added_code = extract_added_code(
                diff
            )

            print(
                "\n===== ADDED CODE ====="
            )

            print(added_code)

            print(
                "======================\n"
            )

            prompt = build_review_prompt(
                added_code,
                changed_files
            )

            print("\n===== FINAL PROMPT SENT TO LLM =====")
            print(prompt)
            print("====================================\n")

            review = review_code(
                prompt
            )

            print(
                "\nPosting Comment To GitHub..."
            )

            try:

                post_pr_comment(
                    repo_name,
                    pr_number,
                    review
                )

                print(
                    "GitHub Comment Posted Successfully"
                )

            except Exception as e:

                print(
                    f"GitHub Comment Error: {e}"
                )

        else:

            print(
                f"Skipping action: {action}"
            )

    print(
        "\n================================================\n"
    )

    return {
        "status": "success"
    }