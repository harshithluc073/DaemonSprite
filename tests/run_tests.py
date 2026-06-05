import os
import sys

# Set QPA platform to offscreen for headless Qt execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure the project root is in the python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

if __name__ == "__main__":
    print("Launching E2E test suite offscreen...")
    exit_code = pytest.main(["-v", "tests/e2e"])
    sys.exit(exit_code)
