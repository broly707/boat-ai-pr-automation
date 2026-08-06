import sys
sys.path.insert(0, ".")

import re
from ai.severity_classifier import classify_and_group_review, _clean_issue_block, format_issue_block

raw_user_input = """AI Code Review
**

🔴 High Severity
Issue: ** Potential NullPointerException because tvMarks is assigned with findViewById without a null‑check, yet tvMarks is declared as a non‑null lateinit var. If the view with ID R.id.tvText does not exist, the assignment will produce a null value that crashes when accessed.

File: app/src/main/java/com/example/practice/MainActivity.kt
Line: L31

Code:

L31:         tvMarks = findViewById(R.id.tvText)
Reason: findViewById can return null when the view is absent, but tvMarks is a non‑nullable property (lateinit var tvMarks: TextView). Assigning a possible null value violates the non‑null contract and will cause a runtime exception.

Suggestion: Verify that the view exists (e.g., use a safe cast or null‑check) before assigning, or make tvMarks nullable and handle the null case gracefully.
Code:

N/A
🟠 Moderate Severity
Issue: ** calculatePercentage performs a division without guarding against a zero divisor, which can lead to an ArithmeticException or Infinity result when total is zero.

File: app/src/main/java/com/example/practice/MainActivity.kt
Line: L116‑L117

Code:

L116:     private fun calculatePercentage(obtained: Int, total: Int): Double {
L117:         return (obtained.toDouble() / total) * 100
Reason: Dividing by total without checking if total equals zero can cause undefined behavior (division by zero).

Suggestion: Add a guard to handle the case where total is zero (e.g., return 0.0 or throw an explicit exception).
Code:

N/A"""

result = classify_and_group_review(raw_user_input)
sys.stdout.buffer.write(result.encode("utf-8"))
sys.stdout.buffer.write(b"\n")
