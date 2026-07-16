import re

with open("PROJECT_STATUS.md", "r") as f:
    content = f.read()

# Subsystem 7: Capability Registry
new_status = """    *   [x] Subsystem 7: Capability Registry
        *   Status: 100% Complete
        *   Tests: Passing
        *   Architecture: Compliant
        *   Review: Passed"""

content = re.sub(r'    \*   \[[x ]\] Subsystem 7: Capability Registry', new_status, content)

with open("PROJECT_STATUS.md", "w") as f:
    f.write(content)
