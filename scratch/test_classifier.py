import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from ai.severity_classifier import classify_and_group_review

sample_text = """
AI Code Review
Issue: Missing string resource
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: 43
Code: Toast.makeText(this, getString(R.string.msg_counter_incremented), Toast.LENGTH_SHORT).show()
Reason: The string resource "msg_counter_incremented" is not defined in the strings.xml file.
Suggestion: Add the missing string resource to the strings.xml file.

Issue: Unused method calls
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: 55-61
Code: addNumbers(5, 3); subtractNumbers(10, 4); isEven(8); isOdd(7); applyDiscount(100.0); getMaximum(12, 20); reverseText("ChatGPT"); sortNumbers(mutableListOf(5, 2, 8, 1))
Reason: The method calls are not used anywhere in the code.
Suggestion: Remove the unused method calls.

Issue: Missing KEY_COUNT declaration
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: 26
Code: if (savedInstanceState != null) { count = savedInstanceState.getInt(KEY_COUNT, 0) }
Reason: The constant KEY_COUNT is not declared in the same scope.
Suggestion: Move the KEY_COUNT declaration to the same scope or make it accessible.

Issue: Missing string resource for button text
File: app/src/main/res/layout/activity_main.xml
Line: 23
Code: android:text="Count: 0"
Reason: The text "Count: 0" is hardcoded in the layout file.
Suggestion: Define a string resource for the button text and use it in the layout file.

However, upon closer inspection of the code, it appears that the text is actually being updated dynamically in the MainActivity class. The issue is not with the hardcoded text, but rather with the fact that the text is not being defined as a string resource.

Issue: Missing string resource for button text
File: app/src/main/res/layout/activity_main.xml
Line: 23
Code: android:text="Decrement"
Reason: The text "Decrement" is hardcoded in the layout file.
Suggestion: Define a string resource for the button text and use it in the layout file.

However, upon closer inspection of the code, it appears that the text is actually being defined as a string resource is not necessary in this case, as the button text is not being translated or changed dynamically.

The only actual issues found in the provided code are:

Issue: Missing string resource
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: 43
Code: Toast.makeText(this, getString(R.string.msg_counter_incremented), Toast.LENGTH_SHORT).show()
Reason: The string resource "msg_counter_incremented" is not defined in the strings.xml file.
Suggestion: Add the missing string resource to the strings.xml file.

Issue: Unused method calls
File: app/src/main/java/com/example/practice/MainActivity.kt
Line: 55-61
Code: addNumbers(5, 3); subtractNumbers(10, 4); isEven(8); isOdd(7); applyDiscount(100.0); getMaximum(12, 20); reverseText("ChatGPT"); sortNumbers(mutableListOf(5, 2, 8, 1))
Reason: The method calls are not used anywhere in the code.
Suggestion: Remove the unused method calls.
"""

output = classify_and_group_review(sample_text)
print("=== RESULT ===")
print(output)
print("==============")
