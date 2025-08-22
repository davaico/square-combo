#!/usr/bin/env python3
"""
Test runner script for the square-combo project.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    """Run tests based on command line arguments."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Parse command line arguments
    args = sys.argv[1:]

    if "--unit" in args:
        cmd = ["python", "-m", "pytest", "tests/unit/", "-v", "-s"]
    elif "--integration" in args:
        cmd = ["python", "-m", "pytest", "tests/integration/", "-v", "-s"]
    else:
        cmd = ["python", "-m", "pytest", "tests/", "-v", "-s"]

    # Add any additional pytest arguments
    extra_args = [arg for arg in args if not arg.startswith("--")]
    cmd.extend(extra_args)

    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    # Run the tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
