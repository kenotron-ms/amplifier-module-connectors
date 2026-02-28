#!/bin/bash
# Add all issues to GitHub Project #1
# Usage: ./add-issues-to-project.sh

set -e

PROJECT_NUMBER=1
OWNER="kenotron"
REPO="kenotron/amplifier-module-connectors"

echo "🚀 Adding issues to GitHub Project #${PROJECT_NUMBER}..."
echo ""
echo "⚠️  If this fails with 'missing required scopes', run:"
echo "   gh auth refresh -h github.com -s project"
echo ""

# Add all issues
for issue in 1 2 3 4 5 6 7 8 9 10 11; do
    echo "Adding issue #${issue}..."
    gh project item-add $PROJECT_NUMBER \
        --owner $OWNER \
        --url "https://github.com/${REPO}/issues/${issue}" 2>&1 || true
done

echo ""
echo "✅ Done! View your project at:"
echo "   https://github.com/users/${OWNER}/projects/${PROJECT_NUMBER}"
