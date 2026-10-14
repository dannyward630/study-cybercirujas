# Contributing

Thank you. This project is a curriculum maintained like software
([docs/PRINCIPLES.md](docs/PRINCIPLES.md)), so contributing works like it does
in a code repository: a branch, a change, checks that pass, a review. You do
not need an AI key or any paid service for any of it.

## Set up, once

Linux or macOS (on Windows use WSL — Ubuntu — the tooling assumes a POSIX
shell and `.venv/bin`). You need `git`, `make` and Python ≥ 3.11 with `venv`.

```bash
git clone https://github.com/<you>/study-cybercirujas.git    # your fork
cd study-cybercirujas
make setup        # checks prerequisites, creates .venv, installs `teach`, enables the git hooks
make test         # every fast test, offline (~1.5 min)
```

`make setup` runs `make preflight` first and stops with the exact package to
install if something is missing. It also sets `core.hooksPath` to `.githooks`:
the pre-commit hook refuses content below the quality floor, content without
provenance, a syllabus status that disagrees with disk, and anything shaped
like an API key. It runs in under a second. Do not bypass it with
`--no-verify`; if you must, say why in the commit message.

## What you can contribute

| You want to… | Do this | Open first |
|---|---|---|
| **report a wrong explanation** | an issue with the *Content error* template: certification, topic, language, the wrong sentence, and the **official source** that shows it | issue |
| **fix a translation** | edit `certs/<cert>/<topic>/<lang>/content.md` or `exercises.md`; keep code blocks, commands, URLs and headings exactly as in English | PR (*Translation* issue optional) |
| **fix content in English** | edit the `en` file, cite the official source in the PR; translations will follow from it | issue first if it is more than a typo |
| **add or fix a lab** | `teach lab new <cert> <topic>` creates `lab.yaml` + a `break_fix.sh` template (no AI); fill in the TODOs, then `teach lab validate <cert> <topic>`. The runner and the full lab format: `docs/LABS-RUNNER.md` (arriving with the `labs-runner` branch) | *Lab* issue |
| **fix a bug or add a feature** | code in `teach/` or `scripts/`, with a test | *Bug* issue for bugs |
| **change a rule, add a certification family or a language** | a proposal, see [GOVERNANCE.md](GOVERNANCE.md) | RFC |

### Provenance is mandatory

Every `certs/<cert>/<topic>/<lang>/` has a `meta.yaml` saying who or what wrote
it. Generated material records `backend`, `model`, `generated_at` and
`sources` automatically. **When you edit material by hand, keep those fields
and append a record of your edit:**

```yaml
human_edits:
  - date: 2026-10-15
    author: github-handle
    summary: fixed the PV reclaim policy default
    source: https://kubernetes.io/docs/concepts/storage/persistent-volumes/
```

With AI or without it, the same rule: nothing enters the corpus without
saying where it came from.

## Conventions

- **Branches:** `<type>/<short-topic>`, e.g. `fix/cka-1.1-reclaim-policy`,
  `i18n/es-cks-3.2`, `lab/lpi-010-160-2.3`.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/):
  `fix(cka): …`, `feat(labs): …`, `docs: …`, `test: …`, `i18n(es): …`. The body
  says *why*.
- **Language:** code, comments, commit messages and project docs in English.
  Study material in the language it is written for.
- **Small pull requests**, one concern each. Generated files (STATUS.md,
  MODELS.md, the README table, the API table) are regenerated, never edited
  by hand: `teach status`, `scripts/gen_readme_table.py`, `scripts/gen_api_docs.py`.

## Checks that must pass

All of them run without keys, without a model, and without network beyond
installing dependencies. CI runs the same targets.

| Flow | Test | Command |
|---|---|---|
| clone → setup → serve → site, API, CLI → Docker lab → cleanup | `tests/e2e/clone_and_run.sh` | `make test-e2e` (needs Docker for the lab step; clones your **committed** HEAD) |
| the site, the API and the student CLI, offline | `tests/test_smoke.py` | `make smoke` |
| determinism: derived files and validators twice, byte for byte, network and models blocked | `tests/test_determinism.py` | `make determinism` |
| labs: every lab honours the contract; `lab new` produces a valid lab; broken specs are caught; `lab up` attaches stdin | `tests/test_labs.py` | `make test` |
| translation: the structural gate a translation must pass (code blocks, URLs, headings, length) | `tests/test_translation_verify.py` | `make test` |
| content: quality floor, manifests, Kubernetes APIs, provenance, sources, syllabus, versions; README/API tables up to date | `scripts/check_*.py`, `gen_*.py --check` | `make verify-ci` |
| everything fast above, in one go | `tests/` | `make test` |

Lab lifecycle in a container (run → break → verify → cleanup per lab) joins
`make test-e2e` with the lab runner; until then `tests/test_labs.py` carries a
skipped placeholder so the gap is visible.

A lab that is known to be broken is listed, with the reason, in
`tests/fixtures/labs_known_broken.txt`; fixing it means deleting its line.

## Reviews

A maintainer ([GOVERNANCE.md](GOVERNANCE.md)) reviews every pull request.
Content changes are judged against the official source, not against opinion.
By contributing you agree your contribution is licensed under
[Apache 2.0](LICENSE), and you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
