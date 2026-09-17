#!/usr/bin/env bash
set -euo pipefail

# Script: sync_hf_space.sh
# Purpose: Synchronize local changes to Hugging Face Spaces demo

SPACE_NAME="LoneVertex/customer-support-rag-demo"
SPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../customer-support-rag-demo-space" && pwd)"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Synchronizing Knowledge Base sample data..."
cp "${ROOT_DIR}/frontend/data/sample_kb.json" "${SPACE_DIR}/kb.json"

echo "==> Uploading space assets to Hugging Face (${SPACE_NAME})..."
hf upload "${SPACE_NAME}" "${SPACE_DIR}" . --repo-type space --commit-message "chore: sync showcase assets with main repository"

echo "==> Verifying Space status..."
hf spaces info "${SPACE_NAME}" --expand runtime

echo "==> Sync complete! Space is live at: https://lonevertex-customer-support-rag-demo.static.hf.space"
