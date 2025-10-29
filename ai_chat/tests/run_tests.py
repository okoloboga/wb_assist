"""
Test runner script for AI Chat Service.

Usage:
    python -m ai_chat.tests.run_tests
    python -m ai_chat.tests.run_tests --unit-only
    python -m ai_chat.tests.run_tests --integration-only
    python -m ai_chat.tests.run_tests --coverage
"""

import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """Run tests with pytest."""
    base_args = ["pytest"]
    
    if args:
        if "--unit-only" in args:
            base_args.extend(["-m", "unit"])
        elif "--integration-only" in args:
            base_args.extend(["-m", "integration"])
        
        if "--coverage" in args:
            base_args.extend(["--cov=ai_chat", "--cov-report=html", "--cov-report=term"])
        
        if "--verbose" in args or "-v" in args:
            base_args.append("-vv")
    else:
        base_args.append("-v")
    
    # Add tests directory
    tests_dir = Path(__file__).parent
    base_args.append(str(tests_dir))
    
    print(f"Running: {' '.join(base_args)}")
    result = subprocess.run(base_args)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests(sys.argv[1:]))

