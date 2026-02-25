#!/usr/bin/env python3
"""
Test runner for Telegram Controller
"""

import os
import sys
import subprocess

def run_tests():
    """Run all tests in the test directory"""
    print("Running Telegram Controller tests...")
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    try:
        # Run pytest on test directory
        result = subprocess.run([sys.executable, '-m', 'pytest', 'test/', '-v'], 
                              capture_output=True, text=True, cwd=project_dir)
        
        print("Test Results:")
        print("=" * 50)
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)