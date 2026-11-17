# Source: Duke, original work for Solomon (2026-11-16).
# What this script does: reruns the standalone proof for the staged GQ-01
# part from a clean state - installs the named dependencies at the staged
# root, builds the core package with the project's own tsdown build (the
# PACKAGE_VERSION value is the core package version, 4.5.1, from its staged
# package.json), then runs the harness.
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npm install --no-audit --no-fund
cd packages/core
../../node_modules/.bin/tsdown --env.PACKAGE_VERSION=4.5.1
cd ../..
node Proof_V1/Harness_V1.js
