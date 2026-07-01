import os
import glob

def replace_in_file(filepath, old_text, new_text):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()
    new_content = content.replace(old_text, new_text)
    if content != new_content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

# Python SDK
for path in glob.glob('/Users/anubhavdhawan/Documents/mcp-toolbox-sdk-python/**/integration.cloudbuild.yaml', recursive=True):
    replace_in_file(path, "_TOOLBOX_VERSION: 'mcp-v202606'", "_TOOLBOX_VERSION: 'v1.6.0'")

# JS SDK
replace_in_file('/Users/anubhavdhawan/Documents/mcp-toolbox-sdk-js/.ci/integration.cloudbuild.yaml', "mcp-v202606", "v1.6.0")

# Go SDK
replace_in_file('/Users/anubhavdhawan/Documents/mcp-toolbox-sdk-go/.ci/integration.cloudbuild.yaml', "mcp-v202606", "v1.6.0")
replace_in_file('/Users/anubhavdhawan/Documents/mcp-toolbox-sdk-go/tests/e2e/e2e_test.go', "mcp-v202606", "v1.6.0")

print("Done")
