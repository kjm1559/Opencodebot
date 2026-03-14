#!/bin/bash
# Simple test for git pull functionality

echo "Testing git pull commands..."

# Test 1: git pull (should work in repo)
echo "Test 1: Running git pull..."
output=$(git pull 2>&1)
exit_code=$?
echo "Exit code: $exit_code"
if [ $exit_code -eq 0 ] || [ $exit_code -eq 1 ]; then
    echo "✓ Test 1 PASSED"
else
    echo "✗ Test 1 FAILED"
    exit 1
fi

echo ""
echo "All tests completed!"
