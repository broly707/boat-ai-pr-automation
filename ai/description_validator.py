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

    # --- Immediate Fast Check for Empty Description ---
    if not pr_body:
        print("Validation Result: FAIL (Empty Body)")
        return False, "PR description is empty. Please explain what this PR does."

    prompt = f"""
You are a strict Pull Request description validator.

Evaluate the following PR Description:
"{pr_body}"

(PR Title for context: "{pr_title}")

Validation Rules:
1. FAIL if the description is gibberish, random text (e.g. "asdf", "qwerty"), or keyboard mashing.
2. FAIL if the description is a meaningless placeholder (e.g. "test", "todo", "fix bug", "update", "N/A", "done", "fixed").
3. FAIL if the description is too short, a single word/phrase, or lacks meaningful explanation of what changed.
4. PASS only if it is a clear, coherent explanation of what the PR actually does.

You MUST respond in this exact two-line format with no extra markdown:
Verdict: PASS or FAIL
Reason: <one short sentence explaining why>
"""

    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("[WARNING] GROQ_API_KEY not found in environment variables.")
            return _local_heuristic_validation(pr_body)

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

        # Robust regex matching for Verdict and Reason (handles formatting variations like **Verdict:** or spaces)
        verdict_match = re.search(r"Verdict\s*:\s*(PASS|FAIL)", response_text, re.IGNORECASE)
        reason_match = re.search(r"Reason\s*:\s*(.+)", response_text, re.IGNORECASE)

        if verdict_match and reason_match:
            verdict = verdict_match.group(1).upper()
            reason = reason_match.group(1).strip()
            # Clean markdown bold/italics wrappers from reason if present
            reason = re.sub(r"^\*+|\*+$", "", reason).strip()
            is_valid = (verdict == "PASS")
            return is_valid, reason

        # Fallback if regex parsing failed to match standard format
        print("[WARNING] Could not parse LLM response format cleanly.")
        return _local_heuristic_validation(pr_body)

    except Exception as e:
        print(f"PR Description Validation Error: {e}")
        return _local_heuristic_validation(pr_body)


def _local_heuristic_validation(pr_body: str) -> tuple[bool, str]:
    """Fallback validation heuristic when LLM API is unavailable or response format parsing fails."""
    if not pr_body:
        return False, "PR description is empty. Please explain what this PR does."

    clean_body = pr_body.lower().strip()
    words = clean_body.split()

    placeholders = {
        "test", "asdf", "qwerty", "n/a", "todo", "fix",
        "update", "fix bug", "done", "fixed", "changes", "wip"
    }

    if clean_body in placeholders or (len(words) <= 2 and words[0] in placeholders):
        return False, f"PR description '{pr_body}' is a placeholder. Please describe the actual changes made."

    if len(words) < 4:
        return False, f"PR description '{pr_body}' is too brief. Please provide a complete sentence explaining your changes."

    return True, "Passed description validation."
