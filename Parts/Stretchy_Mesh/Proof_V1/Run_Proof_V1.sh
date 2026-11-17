#!/bin/sh
# Run_Proof_V1.sh - installs the part's named dependency and
# runs the mesh coverage proof. Duke - original work.
set -e
cd "$(dirname "$0")/.."
npm install --no-audit --no-fund
node Proof_V1/Harness_V1.mjs
