import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, r"e:\boat-ai-pr-automation")

from github.diff_extractor import extract_added_code

sample_diff = """diff --git a/app/src/main/AndroidManifest.xml b/app/src/main/AndroidManifest.xml
index d4db932..f13c7b7 100644
--- a/app/src/main/AndroidManifest.xml
+++ b/app/src/main/AndroidManifest.xml
@@ -10,6 +10,15 @@
         android:label="@string/app_name"
         android:roundIcon="@mipmap/ic_launcher_round"
         android:supportsRtl="true"
-        android:theme="@style/Theme.Practice" />
+        android:theme="@style/Theme.Practice">
+        <activity
+            android:name=".MainActivity"
+            android:exported="true">
+            <intent-filter>
+                <action android:name="android.intent.action.MAIN" />
+                <category android:name="android.intent.category.LAUNCHER" />
+            </intent-filter>
+        </activity>
+    </application>
 
 </manifest>
"""

result = extract_added_code(sample_diff)
print("=== EXTRACTED CODE WITH REAL LINE NUMBERS ===")
print(result)
print("=============================================")
