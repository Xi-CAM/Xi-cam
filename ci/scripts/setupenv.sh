#!/bin/bash

repo_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." >/dev/null 2>&1 && pwd )"

if [ -z "$GITHUB_WORKSPACE" ]; then
    GITHUB_WORKSPACE="$repo_root"
    export GITHUB_WORKSPACE
fi
#echo "$GITHUB_WORKSPACE"

