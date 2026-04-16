#!/usr/bin/env bash
# Resync the framework bundle from johnny-os canonical source.
# Run after johnny-os ships a new release (v1.1.1, v1.2, etc.).
set -euo pipefail
JOHNNY_OS_CLONE="${1:?usage: scripts/resync-bundle.sh <path-to-johnny-os-clone> <release-tag-or-SHA>}"
RELEASE="${2:?usage: scripts/resync-bundle.sh <path-to-johnny-os-clone> <release-tag-or-SHA>}"
pushd "$JOHNNY_OS_CLONE" >/dev/null
git fetch origin
git checkout "$RELEASE"
popd >/dev/null
rm -rf frameworks/llm-dev-v1
cp -r "$JOHNNY_OS_CLONE/frameworks/llm-dev-v1" frameworks/llm-dev-v1
bash frameworks/llm-dev-v1/scripts/verify-all.sh
echo "bundle resynced from johnny-os@$RELEASE"
