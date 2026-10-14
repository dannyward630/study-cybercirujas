#!/usr/bin/env bash
# The break-and-fix lab step of the end-to-end test, isolated so it only ever
# touches what it created itself.
#
#   tests/e2e/lab_step.sh <repo-dir>
#
# Exit codes: 0 = lab brought up, broken, verified and removed; 1 = a check
# failed; 3 = skipped on purpose (no Docker, or a container with the lab's name
# already exists — that is someone's lab, possibly a student's work, and this
# test must not adopt or delete it).
#
# Ownership is a per-run token, not a name or a timestamp: TEACH_LAB_OWNER makes
# `teach lab up` stamp the container with a label at creation (one atomic
# `docker run`), and makes `teach lab down` remove only containers carrying
# that label. Every check here, and the EXIT trap, selects by that label, so a
# container that merely holds the name — created before, or by someone else
# during the run — is never adopted or deleted.
# tests/test_e2e_isolation.py and tests/test_labs_ownership.py prove it.
set -euo pipefail

REPO="${1:?usage: lab_step.sh <repo-dir>}"
TEACH="${TEACH:-$REPO/.venv/bin/teach}"
LAB_CERT="${LAB_CERT:-lpi-010-160}" LAB_TOPIC="${LAB_TOPIC:-2.1}"
name="teach-${LAB_CERT}-${LAB_TOPIC//./-}"
TEACH_LAB_OWNER="e2e-$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
export TEACH_LAB_OWNER
LABEL="org.cybercirujas.study.owner=$TEACH_LAB_OWNER"

ok()   { printf '   ok  %s\n' "$*"; }
fail() { printf '   FAIL %s\n' "$*" >&2; exit 1; }
ours() { docker ps -aq --no-trunc --filter "label=$LABEL"; }

cleanup() {
    # Only containers carrying this run's token: whatever else holds the name
    # is not ours.
    for id in $(ours 2>/dev/null); do docker rm -f "$id" >/dev/null 2>&1 || true; done
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "   SKIP docker not available — the lab step was not tested"
    exit 3
fi
if docker inspect "$name" >/dev/null 2>&1; then
    echo "   SKIP a container named $name already exists and is not ours — left untouched"
    exit 3
fi

cd "$REPO"
up="$(echo SI | "$TEACH" lab up "$LAB_CERT" "$LAB_TOPIC")" || fail "teach lab up $LAB_CERT $LAB_TOPIC"
id="$(ours)"
[ "$(wc -w <<<"$id")" -eq 1 ] || fail "expected exactly one container with this run's token, found: ${id:-none}"
grep -q "Enter it:" <<<"$up" && ok "teach lab up $LAB_CERT $LAB_TOPIC" || fail "teach lab up printed no way in"

docker exec -u student "$id" test -f /home/student/.bashrc.backup-lab-2.1 \
    && ok "the lab actually broke something" || fail "the lab actually broke something"

grep -q destroyed <<<"$("$TEACH" lab down "$LAB_CERT" "$LAB_TOPIC")" && ok "teach lab down" || fail "teach lab down"
[ -z "$(ours)" ] && ok "container removed" || fail "container removed"
