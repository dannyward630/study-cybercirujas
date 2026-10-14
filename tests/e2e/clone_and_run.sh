#!/usr/bin/env bash
# End to end, exactly as a newcomer does it: clone -> make setup -> make serve
# -> site, API and CLI -> a break-and-fix lab in Docker -> clean up.
#
#   tests/e2e/clone_and_run.sh                  # clones this working copy's HEAD
#   SRC=https://github.com/villadalmine/study-cybercirujas.git tests/e2e/clone_and_run.sh
#
# Offline after the clone and the pip install: the server runs with
# TEACH_OFFLINE=1. Needs git, make, python3 (>= 3.11, with venv), curl; the lab
# step needs docker and is skipped, loudly, without it. `make test-e2e` runs
# this; so does CI.
set -euo pipefail

SRC="${SRC:-$(git -C "$(dirname "$0")/../.." rev-parse --show-toplevel)}"
WORK="$(mktemp -d)"
PORT="${PORT:-$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')}"
LAB_CERT=lpi-010-160 LAB_TOPIC=2.1
pass=0
step() { printf '\n== %s\n' "$*"; }
ok()   { pass=$((pass+1)); printf '   ok  %s\n' "$*"; }
fail() { printf '   FAIL %s\n' "$*" >&2; exit 1; }

cleanup() {
    [ -n "${SERVER_PID:-}" ] && kill -- "-$SERVER_PID" 2>/dev/null || true
    if [ -x "$WORK/repo/.venv/bin/teach" ] && command -v docker >/dev/null 2>&1; then
        (cd "$WORK/repo" && .venv/bin/teach lab down $LAB_CERT $LAB_TOPIC >/dev/null 2>&1) || true
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

step "clone $SRC"
git clone -q "$SRC" "$WORK/repo" && ok "cloned ($(du -sh "$WORK/repo" | cut -f1))"
cd "$WORK/repo"

step "make setup"
make -s setup >/dev/null && [ -x .venv/bin/teach ] && ok "venv + teach CLI"

step "make serve on :$PORT (offline)"
TEACH_OFFLINE=1 setsid make -s serve PORT="$PORT" >"$WORK/serve.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 60); do curl -sf "localhost:$PORT/healthz" >/dev/null && break; sleep 1; done
curl -sf "localhost:$PORT/healthz" >/dev/null || { cat "$WORK/serve.log"; fail "server did not start"; }
ok "server up"

B="http://localhost:$PORT"
get() { curl -sf "$B$1"; }
get / | grep -qi "<html"                                        && ok "web /"
get /docs | grep -qi swagger                                     && ok "API docs /docs"
get /api/catalog | python3 -c 'import json,sys; d=json.load(sys.stdin); assert "cka" in d' && ok "/api/catalog lists cka"
get /api/status | python3 -c 'import json,sys; r=[x for x in json.load(sys.stdin) if x["id"]=="cka"][0]; assert r["generated"]==r["topics"]' && ok "/api/status: cka complete"
for lang in en es; do
  get "/api/certs/cka/topics/1.1?lang=$lang" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['lang']=='$lang' and len(d['content'])>1000 and d['generated_by']['model']" && ok "topic cka/1.1 in $lang, with provenance"
done
get "/api/certs/cka/topics/1.1?lang=ja" | python3 -c 'import json,sys; assert json.load(sys.stdin)["lang_fallback"]=="en"' && ok "missing language falls back to en, and says so"
get "/api/search?q=etcd" | python3 -c 'import json,sys; assert json.load(sys.stdin)["hits"]' && ok "/api/search"

step "student CLI"
.venv/bin/teach cert list | grep -q '^cka '                      && ok "teach cert list"
.venv/bin/teach cert show cka | grep -q '1.1'                    && ok "teach cert show cka"
.venv/bin/teach lab validate --all | tail -1 | grep -q ' 0 problem' && ok "teach lab validate --all"

step "break-and-fix lab in Docker"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo SI | .venv/bin/teach lab up $LAB_CERT $LAB_TOPIC | grep -q "Enter it:" && ok "teach lab up $LAB_CERT $LAB_TOPIC"
    name="teach-${LAB_CERT}-${LAB_TOPIC//./-}"
    docker exec -u student "$name" test -f /home/student/.bashrc.backup-lab-2.1 && ok "the lab actually broke something"
    .venv/bin/teach lab down $LAB_CERT $LAB_TOPIC | grep -q destroyed && ok "teach lab down"
    ! docker ps -a --format '{{.Names}}' | grep -qx "$name" && ok "container removed"
else
    echo "   SKIP docker not available — the lab step was not tested"
fi

printf '\nPASS: %d checks, clone to cleanup\n' "$pass"
