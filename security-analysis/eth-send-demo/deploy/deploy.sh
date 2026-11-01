#!/bin/bash
# Deploy Blockchain-Analyzer auf den netcup-Server
# Aufruf aus dem Projektordner: ./deploy/deploy.sh
set -euo pipefail

SSH="ssh -i ~/.ssh/subsumio root@159.195.113.101"
DEST=/opt/blockchain-analyzer

echo "→ Sync nach $DEST"
rsync -az -e "ssh -i ~/.ssh/subsumio" \
  --exclude "__pycache__" --exclude "*.pyc" --exclude ".vercel" \
  --exclude ".devin" --exclude ".git" \
  api modules poison requirements.txt Dockerfile deploy \
  root@159.195.113.101:$DEST/

echo "→ Build + Restart"
$SSH "cd $DEST/deploy && docker compose up -d --build"

echo "→ Warte auf Healthcheck"
sleep 8
$SSH 'docker ps --format "{{.Names}} {{.Status}}" | grep blockchain-analyzer'

echo "✓ Live: http://159.195.113.101:5001/"
