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
# Ownership is tracked by container ID, not by name: the CLI names labs
# teach-<cert>-<topic>, and a name can be reused by someone else while this
# runs. Right after `lab up` the step records the ID of the container that
# carries the name and checks it was created during this run; every later
# check and both teardown paths use that ID, and `teach lab down` (which works
# by name) is only called while the name still points at that ID.
# tests/test_e2e_isolation.py proves a pre-existing container survives.
set -euo pipefail

REPO="${1:?usage: lab_step.sh <repo-dir>}"
TEACH="${TEACH:-$REPO/.venv/bin/teach}"
LAB_CERT="${LAB_CERT:-lpi-010-160}" LAB_TOPIC="${LAB_TOPIC:-2.1}"
name="teach-${LAB_CERT}-${LAB_TOPIC//./-}"
ours=""   # container ID this run created; empty until then and after removal

ok()   { printf '   ok  %s\n' "$*"; }
fail() { printf '   FAIL %s\n' "$*" >&2; exit 1; }
id_of() { docker inspect -f '{{.Id}}' "$1" 2>/dev/null || true; }
# Creation time in epoch seconds, parsed with Python (BSD date has no -d).
created_at() {
    python3 -c 'import sys, datetime; print(int(datetime.datetime.fromisoformat(sys.argv[1][:19]).replace(tzinfo=datetime.timezone.utc).timestamp()))'         "$(docker inspect -f '{{.Created}}' "$1")"
}
# Docker Desktop runs the daemon in a VM whose clock can drift a little.
SKEW=60

cleanup() {
    # By ID only: whatever holds the name now may not be ours.
    [ -n "$ours" ] && docker rm -f "$ours" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "   SKIP docker not available — the lab step was not tested"
    exit 3
fi
if [ -n "$(id_of "$name")" ]; then
    echo "   SKIP a container named $name already exists and is not ours — left untouched"
    exit 3
fi

cd "$REPO"
started="$(date -u +%s)"
up="$(echo SI | "$TEACH" lab up "$LAB_CERT" "$LAB_TOPIC")" || {
    # lab up may have created the container before failing: claim it only if
    # it is new since this step started.
    id="$(id_of "$name")"
    if [ -n "$id" ] && [ "$(created_at "$id")" -ge $((started - SKEW)) ]; then ours="$id"; fi
    fail "teach lab up $LAB_CERT $LAB_TOPIC"
}
id="$(id_of "$name")"
[ -n "$id" ] || fail "teach lab up left no container named $name"
[ "$(created_at "$id")" -ge $((started - SKEW)) ] || fail "the container named $name predates this run — not ours"
ours="$id"
grep -q "Enter it:" <<<"$up" && ok "teach lab up $LAB_CERT $LAB_TOPIC" || fail "teach lab up printed no way in"

docker exec -u student "$ours" test -f /home/student/.bashrc.backup-lab-2.1 \
    && ok "the lab actually broke something" || fail "the lab actually broke something"

[ "$(id_of "$name")" = "$ours" ] || fail "the name $name no longer points at our container — not calling lab down"
grep -q destroyed <<<"$("$TEACH" lab down "$LAB_CERT" "$LAB_TOPIC")" && ok "teach lab down" || fail "teach lab down"
[ -z "$(id_of "$ours")" ] && ok "container removed" || fail "container removed"
ours=""
