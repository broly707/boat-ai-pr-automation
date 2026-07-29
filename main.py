import json
import hmac
import hashlib
import os
import shutil
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

from github.pr_commenter import (
    post_pr_comment,
    get_pr_details
)

from ai.prompt_builder import build_review_prompt
from ai.reviewer import review_code
from ai.description_validator import validate_pr_description

app = FastAPI()

GITHUB_SECRET = os.environ.get(
    "GITHUB_WEBHOOK_SECRET",
    ""
)


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
            "reopened",
            "edited"
        ]:

            # Always fetch LIVE PR data from GitHub API.
            # This ensures Redeliver scenarios also use the current description.
            payload_title = (pr.get("title") or "").strip()
            payload_body = (pr.get("body") or "").strip()

            live_title, live_body = get_pr_details(repo_name, pr_number)

            # Prefer the richer of live API vs webhook payload (avoids stale/placeholder bodies).
            def _richer_text(primary: str, fallback: str) -> str:
                primary = (primary or "").strip()
                fallback = (fallback or "").strip()
                if not primary:
                    return fallback
                if not fallback:
                    return primary
                return primary if len(primary) >= len(fallback) else fallback

            pr_title = _richer_text(live_title, payload_title)
            pr_body = _richer_text(live_body, payload_body)

            print(f"[DEBUG] Payload body : {payload_body!r}")
            print(f"[DEBUG] Live API body: {live_body!r}")
            print(f"[DEBUG] Final body used for validation: {pr_body!r}")

            print("\nExecuting PR Description Validation Gate...")
            is_valid, validation_reason = validate_pr_description(
                pr_title,
                pr_body
            )

            if not is_valid:
                print(
                    "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                )
                print(
                    f"PR DESCRIPTION VALIDATION GATE >>> FAILED <<<"
                )
                print(
                    f"Reason: {validation_reason}"
                )
                print(
                    "Pipeline STOPPED. Code review will NOT run."
                )
                print(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                )

                try:
                    post_pr_comment(
                        repo_name,
                        pr_number,
                        f"\u274c **PR Description Validation Failed**\n\n**Reason:** {validation_reason}\n\nPlease update your PR description with a clear explanation of what this PR does, then push a new commit to re-trigger the review."
                    )
                    print(
                        "Validation Failure Comment Posted To GitHub Successfully"
                    )
                except Exception as e:
                    print(
                        f"[WARNING] Could not post GitHub comment: {e}"
                    )
                    print(
                        "[WARNING] Check that GITHUB_APP_PRIVATE_KEY, GITHUB_APP_ID, "
                        "and GITHUB_INSTALLATION_ID are set in Render environment variables."
                    )

                return {
                    "status": "failed",
                    "reason": validation_reason
                }

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

            finally:

                # Clean up the cloned workspace to prevent disk buildup
                try:
                    if os.path.exists(workspace_path):
                        shutil.rmtree(workspace_path)
                        print(
                            f"Workspace cleaned up: {workspace_path}"
                        )
                except Exception as cleanup_err:
                    print(
                        f"Workspace Cleanup Warning: {cleanup_err}"
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