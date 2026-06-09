#!/usr/bin/env bash
#
# Deploy the marketing site to hospitalityapp.co.uk on 20i.
#
# Workflow:
#   1. Refuse to deploy a dirty working tree.
#   2. Push local main to GitHub.
#   3. SSH to 20i and `git pull` in ~/site-source/ (the live web root).
#
# Prereqs:
#   - SSH alias `hospitalityapp` configured in ~/.ssh/config
#     (Host hospitalityapp / HostName ssh.lhr.stackcp.com / Port 39355
#      / User hospitalityapp.co.uk / IdentityFile ~/.ssh/id_ed25519)
#   - Public key already added under My20i > Security > SSH Access
#   - Server's git remote authenticates to GitHub (deploy key, set
#     up when site-source/ was first cloned)
#
# Usage:  ./scripts/deploy.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

BRANCH="$(git symbolic-ref --short HEAD)"
HEAD_LOCAL="$(git log -1 --oneline)"

printf '→ Local branch: %s\n' "$BRANCH"
printf '→ Local HEAD:   %s\n' "$HEAD_LOCAL"

if [ "$BRANCH" != "main" ]; then
  printf '✗ Refusing to deploy from %s — main only.\n' "$BRANCH" >&2
  exit 1
fi

if ! git diff-index --quiet HEAD --; then
  printf '✗ Working tree has uncommitted changes. Commit or stash first.\n' >&2
  git status --short >&2
  exit 1
fi

printf '\n→ Pushing main to origin (GitHub)...\n'
git push origin main

printf '\n→ Pulling on hospitalityapp.co.uk (~/site-source)...\n'
ssh hospitalityapp 'cd ~/site-source && git pull --ff-only && printf "→ Server HEAD: %s\n" "$(git log -1 --oneline)"'

printf '\n✓ Deploy complete. https://hospitalityapp.co.uk\n'
