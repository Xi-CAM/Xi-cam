#!/bin/bash
# -v verbose
# -E allow ERR trap to fire
# -e bash script exits immediately when a command fails
# -u bash script treats unset variables as error and exits
# -x debug (print commands)
# -o exit code zero only if all commands in pipeline are 0
set -vEeuxo pipefail

repo_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." >/dev/null 2>&1 && pwd )"

if [ -z "$GITHUB_WORKSPACE" ]; then
    GITHUB_WORKSPACE="$repo_root"
    export GITHUB_WORKSPACE
fi
#echo "$GITHUB_WORKSPACE"

