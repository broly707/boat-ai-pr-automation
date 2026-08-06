import sys
sys.path.insert(0, ".")

import re
from ai.severity_classifier import classify_and_group_review

llm_output_sample = """Issue: calculatePercentage does not guard against a zero-value total, which can cause a division-by-zero situation (resulting in Infinity or a runtime exception depending on the runtime).
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: L116-L118
Code:
L116:     private fun calculatePercentage(obtained: Int, total: Int): Double {
L117:         return (obtained.toDouble() / total) * 100
L118:     }
Reason: The method divides by total without checking whether total is zero.
Suggestion: Add a check for total == 0 and handle the case appropriately (e.g., return 0.0 or throw an informative exception).

Code:
N/A

Issue: tvMarks is initialized with a view ID that does not match its variable name, which may indicate the wrong view is being referenced.
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: L31
Code:
L31:         tvMarks = findViewById(R.id.tvText)
Reason: The variable is named tvMarks but the ID used is tvText, suggesting a possible mismatch between the intended TextView and the actual layout resource.
Suggestion: Verify that R.id.tvText is the correct ID for the marks TextView; rename the ID or variable for consistency.

Code:
N/A"""

formatted = classify_and_group_review(llm_output_sample)
sys.stdout.buffer.write(formatted.encode("utf-8"))
sys.stdout.buffer.write(b"\n")
