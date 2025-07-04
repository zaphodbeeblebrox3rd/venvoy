#!/bin/bash
# Test script to verify venvoy upgrade command fix

echo "🧪 Testing venvoy upgrade command fix"
echo "====================================="

# Test 1: Basic upgrade command
echo ""
echo "Test 1: Basic upgrade command"
echo "Running: venvoy upgrade"
if venvoy upgrade 2>&1 | grep -q "unexpected extra argument"; then
    echo "❌ FAIL: Still getting 'unexpected extra argument' error"
else
    echo "✅ PASS: No 'unexpected extra argument' error"
fi

# Test 2: Upgrade with help flag
echo ""
echo "Test 2: Upgrade with help flag"
echo "Running: venvoy upgrade --help"
if venvoy upgrade --help 2>&1 | grep -q "unexpected extra argument"; then
    echo "❌ FAIL: Still getting 'unexpected extra argument' error with --help"
else
    echo "✅ PASS: No 'unexpected extra argument' error with --help"
fi

# Test 3: Check if upgrade and update produce same output
echo ""
echo "Test 3: Comparing upgrade vs update output"
UPGRADE_OUTPUT=$(venvoy upgrade 2>&1 | head -5)
UPDATE_OUTPUT=$(venvoy update 2>&1 | head -5)

if [ "$UPGRADE_OUTPUT" = "$UPDATE_OUTPUT" ]; then
    echo "✅ PASS: upgrade and update produce same output"
else
    echo "❌ FAIL: upgrade and update produce different output"
    echo "Upgrade output: $UPGRADE_OUTPUT"
    echo "Update output: $UPDATE_OUTPUT"
fi

echo ""
echo "�� Test completed!" 