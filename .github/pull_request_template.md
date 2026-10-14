## What and why

<!-- One concern per pull request. Link the issue or RFC it answers. -->

## Kind

- [ ] content fix (official source: )
- [ ] translation
- [ ] lab (`teach lab validate <cert> <topic>` passes)
- [ ] code / checks
- [ ] docs

## Checklist

- [ ] `make test` passes locally (offline, no key)
- [ ] `make verify-ci` passes
- [ ] material I edited by hand keeps its `meta.yaml` and records my edit under `human_edits`
- [ ] generated files (STATUS.md, MODELS.md, README/API tables) were regenerated, not hand-edited
- [ ] if this touches the clone-and-run path: `make test-e2e` passes
