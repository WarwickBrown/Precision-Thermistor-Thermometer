#!/usr/bin/env bash
# One-time helper to turn this folder into a git repo and push to GitHub.
# 1) Create an empty repo on GitHub (no README/license) and copy its URL.
# 2) Run:  bash init_git.sh git@github.com:USERNAME/the-box-thermometer.git
set -e
REMOTE="$1"
if [ -z "$REMOTE" ]; then echo "usage: bash init_git.sh <remote-url>"; exit 1; fi
git init
git add .
git commit -m "Initial commit: The Box precision thermistor thermometer"
git branch -M main
git remote add origin "$REMOTE"
git push -u origin main
echo "Pushed to $REMOTE"
