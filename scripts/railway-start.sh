#!/usr/bin/env bash
# Run this from your machine (not CI). Completes Railway login + project link.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Railway CLI ==="
if ! command -v railway >/dev/null 2>&1; then
  echo "Install: npm install -g @railway/cli"
  exit 1
fi

echo "Step 1: Login (browser will open or you'll get a device code)"
railway login

echo ""
echo "Step 2: Link this repo to your Railway project"
railway link

echo ""
echo "Step 3: Who am I?"
railway whoami

echo ""
echo "Done. Next:"
echo "  railway variables --service backend"
echo "  railway logs --service backend"
