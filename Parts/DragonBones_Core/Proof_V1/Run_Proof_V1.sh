#!/bin/sh
# Run_Proof_V1.sh - builds the staged DragonBones core with the
# harness and runs the pose proof. Duke - original work.
set -e
cd "$(dirname "$0")/.."
npm install --no-audit --no-fund
cd Proof_V1
../node_modules/.bin/tsc -p tsconfig.proof.json
node out/proof.js
