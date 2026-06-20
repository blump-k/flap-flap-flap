#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
git add "$1"
git commit -m "${2:-update}"
git push
