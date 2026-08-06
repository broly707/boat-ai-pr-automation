def build_review_prompt(
    code: str,
    changed_files: list
) -> str:

    files_list = "\n".join(
        f"- {f}" for f in changed_files
    ) if changed_files else "- (no files listed)"

    return f"""
Review this code as a senior Team Lead.

Report only issues that are directly supported by the code shown.

Important rules for analysis and false-positive prevention:
- You are analyzing the complete, unmodified source code for the changed files below.
- Do NOT report false-positive issues for existing code structure (such as "Missing class definition", "Missing function definitions", "Unclosed multiline comment", or "Incomplete code"). All classes, functions, KDoc comments, and blocks shown in the input are complete and valid.

Important rules for Line numbers:
- Every line of code below is preprocessed and prefixed with its actual line number from the source file (e.g. L43: <code_content>).
- In the Line: field for each reported issue, specify the exact line number(s) (e.g. 43 or L43 or 55-61) corresponding to the line prefix.
- Do NOT estimate, guess, or invent line numbers. Use ONLY the exact line numbers provided in the input line prefixes.

Important rules for Code section format:
- Always print Code: on its own line followed by a blank line, then render the code snippet wrapped inside a fenced Markdown code block with language syntax highlighting (e.g. ```kotlin ... ``` or ```xml ... ```), preserving all indentation, whitespace, line breaks, and formatting. Never put code inline after Code:. If snippet is N/A or absent, put ```text\nN/A\n``` after blank line.

For each issue provide:

Issue:
File:
Line:

Code:

```<language>
<exact code snippet from source file>
```

Reason:
Suggestion:

Keep the reason and suggestion short and easy to understand.

Do not provide suggested fixes.
Do not provide final code.
Do not assume missing code.
Do not speculate.

Changed Files:

{files_list}

Code:

{code}
"""