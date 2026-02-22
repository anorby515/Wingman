#!/usr/bin/env bash
# Wingman PWA — start script
# Run from the repo root: bash start.sh
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "=== Wingman PWA Startup ==="

# ── 1. Backend deps ───────────────────────────────────────────────────────────
echo ""
echo "→ Installing backend dependencies…"
PIP_CMD="pip"
if ! command -v pip &>/dev/null; then
  PIP_CMD="pip3"
fi
$PIP_CMD install -r backend/requirements.txt -q --break-system-packages 2>/dev/null \
  || $PIP_CMD install -r backend/requirements.txt -q

# ── 2. Frontend build ─────────────────────────────────────────────────────────
DIST="$REPO/frontend/dist"
if [ ! -d "$DIST" ]; then
  echo ""
  echo "→ Building frontend (first run)…"
  cd "$REPO/frontend"
  if ! command -v npm &>/dev/null; then
    echo "  ERROR: npm not found. Install Node.js (https://nodejs.org) then re-run."
    exit 1
  fi
  npm install --silent
  npm run build --silent
  cd "$REPO"
  echo "  Frontend built → frontend/dist/"
else
  echo "→ Frontend dist found (skip build — run 'cd frontend && npm run build' to rebuild)"
fi

# ── 3. Launch backend ─────────────────────────────────────────────────────────
echo ""
echo "→ Starting Wingman API + frontend at http://localhost:8000"
echo "  Press Ctrl+C to stop."
echo ""
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
