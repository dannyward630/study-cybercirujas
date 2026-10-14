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
# The lab name is fixed by the CLI (teach-<cert>-<topic>), so isolation is by
# refusal, not by renaming: if the name is taken, the step is skipped and the
# existing container is left exactly as it was. Cleanup on exit only runs for
# a lab this run created. tests/test_e2e_isolation.py proves the refusal.
set -euo pipefail

REPO="${1:?usage: lab_step.sh <repo-dir>}"
TEACH="${TEACH:-$REPO/.venv/bin/teach}"
LAB_CERT="${LAB_CERT:-lpi-010-160}" LAB_TOPIC="${LAB_TOPIC:-2.1}"
name="teach-${LAB_CERT}-${LAB_TOPIC//./-}"
created=0

ok()   { printf '   ok  %s\n' "$*"; }
fail() { printf '   FAIL %s\n' "$*" >&2; exit 1; }

cleanup() {
    if [ "$created" = 1 ]; then
        (cd "$REPO" && "$TEACH" lab down "$LAB_CERT" "$LAB_TOPIC" >/dev/null 2>&1) || true
    fi
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "   SKIP docker not available — the lab step was not tested"
    exit 3
fi
if docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
    echo "   SKIP a container named $name already exists and is not ours — left untouched"
    exit 3
fi

cd "$REPO"
up="$(echo SI | "$TEACH" lab up "$LAB_CERT" "$LAB_TOPIC")" || fail "teach lab up $LAB_CERT $LAB_TOPIC"
created=1
grep -q "Enter it:" <<<"$up" && ok "teach lab up $LAB_CERT $LAB_TOPIC" || fail "teach lab up printed no way in"
docker exec -u student "$name" test -f /home/student/.bashrc.backup-lab-2.1 \
    && ok "the lab actually broke something" || fail "the lab actually broke something"
grep -q destroyed <<<"$("$TEACH" lab down "$LAB_CERT" "$LAB_TOPIC")" && ok "teach lab down" || fail "teach lab down"
created=0
! docker ps -a --format '{{.Names}}' | grep -qx "$name" && ok "container removed" || fail "container removed"
