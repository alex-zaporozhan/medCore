#!/usr/bin/env bash

set -euo pipefail

# Security audit for frontend dependencies using npm audit script.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/../frontend"

npm run security:audit

