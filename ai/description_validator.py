import os
from groq import Groq


def validate_pr_description(
    title: str,
    body: str
) -> tuple[bool, str]:

    pr_title = (title or "").strip()
    pr_body = (body or "").strip()

    prompt = f"""
Analyze the following Pull Request title and description to validate if it provides a meaningful explanation of what the PR actually does.

Title: {pr_title}
Description: {pr_body}

Evaluation Rules:
1. FAIL if the description is empty, blank, whitespace-only, or an unfilled template.
2. FAIL if the description is gibberish, random characters, or meaningless placeholder text (e.g. "test", "asdf", "N/A", "todo", "fix bug", "update", a single word, generic boilerplate).
3. FAIL if the description does not form coherent, meaningful sentence(s) that explain what the PR actually does.
4. PASS otherwise.

Respond in EXACTLY this two-line format:
Verdict: PASS or FAIL
Reason: <one short sentence>
"""

    print("\n===== PR DESCRIPTION VALIDATION GATE =====")

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
        reason = "PR description failed validation."

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
        return True, "Validation skipped due to API error."
