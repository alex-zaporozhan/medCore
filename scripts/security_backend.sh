#!/usr/bin/env bash

set -euo pipefail

# Security audit for Python backend dependencies using pip-audit.
# Expects pip-audit to be installed in the current environment.

pip-audit --progress-spinner=off

