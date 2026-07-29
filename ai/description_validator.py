import os
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

    # Use a clear placeholder when body is empty so the LLM
    # generates the exact right reason instead of a hardcoded one
    description_for_llm = (
        pr_body if pr_body
        else "(no description provided)"
    )

    prompt = f"""
You are a strict PR description validator. Evaluate ONLY the Description field below.
The Title is provided for context only — do NOT use it to compensate for a bad Description.

PR Title: {pr_title}
PR Description (the field being validated): {description_for_llm}

Validation Rules (apply them strictly to the Description field only):
1. FAIL if the description is empty, missing, or was not provided.
2. FAIL if the description is a single word, two words, or very short with no real meaning.
3. FAIL if the description is gibberish, random characters, or filler text (e.g. "asdf", "test", "N/A", "todo", "update", "fix", "done", generic boilerplate, copy-paste templates with unfilled placeholders).
4. FAIL if the description does not form coherent, meaningful sentence(s) that clearly explain what this PR actually does.
5. PASS only if the description is a proper, human-written explanation of the PR changes.

Respond in EXACTLY this two-line format with no extra text:
Verdict: PASS or FAIL
Reason: <one short sentence explaining the specific reason for the verdict>
"""

    try:
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY")
        )

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

        verdict = "FAIL"
        reason = "PR description does not meet the required standard."

        for line in response_text.splitlines():
            line_clean = line.strip()
            if line_clean.startswith("Verdict:"):
                verdict = line_clean.split(":", 1)[1].strip().upper()
            elif line_clean.startswith("Reason:"):
                reason = line_clean.split(":", 1)[1].strip()

        is_valid = (verdict == "PASS")
        return is_valid, reason

    except Exception as e:
        print(f"PR Description Validation Error: {e}")
        # Only block on empty body if the LLM itself is unavailable
        if not pr_body:
            return (
                False,
                "PR description is missing. Please add a description before requesting a review."
            )
        return True, "Validation skipped due to API error."

