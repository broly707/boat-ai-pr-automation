import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from ai.description_validator import validate_pr_description

test_cases = [
    ("test: trigger PR", ""),
    ("test: trigger PR", "asdfghjkl"),
    ("test: trigger PR", "test"),
    ("test: trigger PR", "fix bug"),
    ("test: trigger PR", "Added user authentication endpoints and updated database schema for user profiles."),
]

print("Running local test of validate_pr_description...\n")

for title, body in test_cases:
    print(f"--- TESTING: Title={title!r}, Body={body!r} ---")
    is_valid, reason = validate_pr_description(title, body)
    print(f"RESULT: is_valid={is_valid}, Reason={reason!r}\n")
