#!/usr/bin/env python3
"""
Test runner script for CogView4 FastAPI tests
"""

import sys
import os
import subprocess
import argparse

def run_tests(test_pattern=None, verbose=False):
    """Run tests with optional pattern matching"""
    
    # Add src directory to Python path for tests that might need it
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    # Change to tests directory
    os.chdir('tests')
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    if test_pattern:
        cmd.append(test_pattern)
    else:
        cmd.append('.')
    
    if verbose:
        cmd.append('-v')
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(['--cov=../src', '--cov-report=term-missing'])
    except ImportError:
        print("pytest-cov not installed, running without coverage")
    
    print(f"Running tests with command: {' '.join(cmd)}")
    
    # Run tests
    result = subprocess.run(cmd)
    return result.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CogView4 FastAPI tests")
    parser.add_argument("--pattern", "-p", help="Test pattern to run (e.g., test_client.py)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    exit_code = run_tests(args.pattern, args.verbose)
    sys.exit(exit_code) 