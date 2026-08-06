from ai.severity_classifier import format_issue_block

block1 = "\n".join([
    "Issue: Missing package attribute",
    "File: app/src/main/AndroidManifest.xml",
    "Line: L2",
    "",
    "Code:",
    'L2: <manifest xmlns:android="http://schemas.android.com/apk/res/android"',
    "",
    "Reason: The package attribute is missing from the manifest tag.",
    "Suggestion: Add the package attribute.",
    "",
    "Code:",
    "N/A",
])

block2 = "\n".join([
    "Issue: Hardcoded string",
    "File: app/src/main/java/com/example/MainActivity.kt",
    "Line: L43",
    'Code: Toast.makeText(this, "Hello", Toast.LENGTH_SHORT).show()',
    "Reason: Hardcoded string literal.",
    "Suggestion: Move to strings.xml.",
])

block3 = "\n".join([
    "Issue: Missing error handling",
    "File: app/src/main/java/com/example/MainActivity.kt",
    "Line: 49-53",
    "Code:",
    "```kotlin",
    "Toast.makeText(",
    "    this,",
    "    getString(R.string.msg),",
    "    Toast.LENGTH_SHORT",
    ").show()",
    "```",
    "Reason: No try-catch.",
    "Suggestion: Wrap in try-catch.",
])

print("=== TEST 1: Duplicate Code: block ===")
print(format_issue_block(block1))
print()
print("=== TEST 2: Inline code ===")
print(format_issue_block(block2))
print()
print("=== TEST 3: Fenced code block ===")
print(format_issue_block(block3))
