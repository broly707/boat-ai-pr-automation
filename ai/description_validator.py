import os
import re
from groq import Groq


def validate_pr_description(
    title: str,
    body: str
) -> tuple[bool, str]:

    pr_title = (title or "").strip()
    pr_body = (body or "").strip()

    print("\n===== PR DESCRIPTION VALIDATION GATE =====")
    print(f"Title: {pr_title!r}")
    print(f"Body : {pr_body!r}")

    # --- Fast pre-check: empty body is an instant FAIL ---
    # Do NOT pass "(empty)" to the LLM — it reads it as gibberish text
    if not pr_body:
        print("Validation Result: FAIL (description is empty)")
        return (
            False,
            "PR description is empty — please describe what this PR does."
        )

    prompt = f"""
You are a strict Pull Request description validator.

Evaluate the following PR details:
PR Title: {pr_title if pr_title else "(no title)"}
PR Description: {pr_body}

Validation Rules:
1. FAIL if the PR description is empty, missing, or blank.
2. FAIL if the description or title is gibberish, random text (e.g. "asdf", "qwerty", "zxcv"), or keyboard mashing.
3. FAIL if the description or title is a meaningless placeholder (e.g. "test", "todo", "fix bug", "update", "N/A", "done", "fixed", "wip").
4. FAIL if the description does not form coherent, meaningful sentence(s) that clearly explain what this PR actually does.
5. PASS only if there is a clear, meaningful explanation of what the PR changes and why.

You MUST respond in this exact two-line format with no extra markdown:
Verdict: PASS or FAIL
Reason: <one short sentence explaining the exact reason>
"""

    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("[WARNING] GROQ_API_KEY not found in environment variables. Using heuristic validation.")
            return _local_heuristic_validation(pr_title, pr_body)

        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=150,
            top_p=1,
            stream=False
        )

        response_text = (
            completion.choices[0].message.content or ""
        ).strip()

        print("\n===== VALIDATION LLM RESPONSE =====")
        print(response_text)
        print("===================================\n")

        # Robust regex matching for Verdict and Reason
        verdict_match = re.search(r"Verdict\s*:\s*(PASS|FAIL)", response_text, re.IGNORECASE)
        reason_match = re.search(r"Reason\s*:\s*(.+)", response_text, re.IGNORECASE)

        if verdict_match and reason_match:
            verdict = verdict_match.group(1).upper()
            reason = reason_match.group(1).strip()
            # Clean markdown bold/italics wrappers from reason if present
            reason = re.sub(r"^\*+|\*+$", "", reason).strip()
            is_valid = (verdict == "PASS")
            return is_valid, reason

        print("[WARNING] Could not parse LLM response format cleanly. Using heuristic validation.")
        return _local_heuristic_validation(pr_title, pr_body)

    except Exception as e:
        print(f"PR Description Validation Error: {e}. Using heuristic validation.")
        return _local_heuristic_validation(pr_title, pr_body)


def _local_heuristic_validation(pr_title: str, pr_body: str) -> tuple[bool, str]:
    """Fallback validation heuristic when LLM API is unavailable."""
    title_clean = (pr_title or "").strip()
    body_clean = (pr_body or "").strip()

    placeholders = {
        "test", "asdf", "qwerty", "n/a", "todo", "fix",
        "update", "fix bug", "done", "fixed", "changes", "wip", "no description"
    }

    # 1. Evaluate body if present
    if body_clean:
        body_words = body_clean.lower().split()
        if body_clean.lower() in placeholders or (len(body_words) <= 2 and body_words[0] in placeholders):
            return False, f"PR description '{body_clean}' is placeholder/meaningless text."
        if len(body_words) < 4:
            return False, f"PR description '{body_clean}' is too short (fewer than 4 words)."
        return True, "Passed description validation."

    # 2. If body is empty, evaluate title for context
    if title_clean:
        title_words = title_clean.lower().split()
        if title_clean.lower() in placeholders or (len(title_words) <= 2 and title_words[0] in placeholders):
            return False, f"PR description is missing and PR title '{title_clean}' is a meaningless placeholder."
        return False, f"PR description is empty for PR titled '{title_clean}'. Please add a detailed description."

    return False, "PR title and description are both missing."
