#!/usr/bin/env python3
"""Check a pull request's description: sections, title, and declared provenance.

The PR format is the same whoever wrote the change, a person or a model
(.github/PULL_REQUEST_TEMPLATE/, CONTRIBUTING.md). This makes the format a
check instead of a request. It fails when:

- a required section is missing or empty (HTML comments do not count);
- the title is not a Conventional Commit;
- the "Site:" line in the Kind section is missing or disagrees with the
  computed site impact: `image-rebuild` when the PR touches anything the
  public image is built from (the `paths` of .github/workflows/docker.yml,
  the single source), `none` otherwise;
- the PR touches study material under certs/ and the provenance it declares
  does not match the meta.yaml of the topics it touches: for `Author: ai`, the
  declared backend and model must be the ones meta.yaml records; for
  `Author: human`, every touched meta.yaml must carry a `human_edits` entry.

No network, no model: it reads the PR body, the list of changed files and the
meta.yaml files in the checkout.

    scripts/check_pr.py --title "docs: x" --body-file body.md --files a b c
    scripts/check_pr.py --event "$GITHUB_EVENT_PATH" --base origin/main   # CI
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent

SECTIONS = ("What and why", "Kind", "Provenance", "Evidence",
            "How to test it from a clean clone", "Risk and rollback", "Depends on")
TYPES = ("feat", "fix", "docs", "test", "ci", "chore", "refactor", "perf", "build",
         "style", "revert", "i18n", "content", "lab", "video")
TITLE = re.compile(rf"^({'|'.join(TYPES)})(\([\w./,-]+\))?!?: \S.*$")
# certs/<cert>/<topic>/<lang>/<file> — the material that carries a meta.yaml.
MATERIAL = re.compile(r"^certs/([^/]+)/([^/]+)/([a-z]{2})/[^/]+$")


def sections(body: str) -> dict[str, str]:
    """`## Heading` → its text, with HTML comments removed."""
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    found: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1)
            found[current] = ""
        elif current is not None:
            found[current] += line + "\n"
    return {k: v.strip() for k, v in found.items()}


def declared(provenance: str) -> dict[str, str]:
    """`- Key: value` lines of the Provenance section, lower-cased keys."""
    out = {}
    for line in provenance.splitlines():
        match = re.match(r"^\s*[-*]\s*([A-Za-z ]+):\s*(.*?)\s*$", line)
        if match:
            out[match.group(1).strip().lower()] = match.group(2)
    return out


def image_paths() -> list[str]:
    """What triggers an image rebuild: docker.yml's push paths, read, not copied."""
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))  # YAML 1.1 reads `on:` as True
    return list(triggers["push"]["paths"])


def _glob(pattern: str) -> re.Pattern:
    """GitHub path filter semantics: `**` crosses directories, `*` does not."""
    out = ""
    for part in re.split(r"(\*\*|\*)", pattern):
        out += ".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part)
    return re.compile(out + "$")


def site_impact(files: list[str]) -> str:
    patterns = [_glob(p) for p in image_paths()]
    hit = any(p.match(f.replace("\\", "/")) for f in files for p in patterns)
    return "image-rebuild" if hit else "none"


def material_dirs(files: list[str]) -> list[Path]:
    dirs = {Path(*Path(f).parts[:4]) for f in files if MATERIAL.match(f.replace("\\", "/"))}
    return sorted(dirs)


def check(title: str, body: str, files: list[str], root: Path = REPO) -> list[str]:
    problems: list[str] = []
    if not TITLE.match(title.strip()):
        problems.append(f"title is not a Conventional Commit ({'|'.join(TYPES)}(scope)?: summary): {title!r}")
    found = sections(body)
    for name in SECTIONS:
        if name not in found:
            problems.append(f"missing section: ## {name}")
        elif not found[name]:
            problems.append(f"empty section: ## {name}")

    impact = site_impact(files)
    site = re.search(r"^\s*[-*]?\s*Site:\s*(\S+)", found.get("Kind", ""), re.M)
    if not site:
        problems.append(f"Kind: add a 'Site: {impact}' line (computed from the changed files)")
    elif site.group(1).strip("`") != impact:
        problems.append(f"Kind: says Site: {site.group(1)}, but the changed files make it "
                        f"'{impact}' (image paths: .github/workflows/docker.yml)")

    dirs = material_dirs(files)
    if not dirs or "Provenance" not in found:
        return problems
    prov = declared(found["Provenance"])
    author = prov.get("author", "").lower()
    if author not in ("ai", "human"):
        problems.append("Provenance: 'Author:' must be 'ai' or 'human' when certs/ material changes")
        return problems
    for directory in dirs:
        meta_file = root / directory / "meta.yaml"
        if not meta_file.exists():
            problems.append(f"{directory}: no meta.yaml — material without provenance")
            continue
        meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        if author == "ai":
            for key in ("backend", "model"):
                want = str(meta.get(key, ""))
                said = [v.strip() for v in prov.get(key, "").split(",") if v.strip()]
                if want not in said:
                    problems.append(f"{directory}: Provenance says {key} {prov.get(key)!r}, "
                                    f"meta.yaml says {want!r}")
        elif not meta.get("human_edits"):
            problems.append(f"{directory}: Author is human but meta.yaml has no human_edits "
                            "entry (CONTRIBUTING.md → Provenance is mandatory)")
    return problems


def changed_files(base: str) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                            cwd=REPO, capture_output=True, text=True, check=True)
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event", help="GitHub event JSON (pull_request)")
    parser.add_argument("--title")
    parser.add_argument("--body-file")
    parser.add_argument("--base", help="git ref to diff against, e.g. origin/main")
    parser.add_argument("--files", nargs="*", default=None)
    parser.add_argument("--label-file", help="write the site label here (for the labelling step)")
    args = parser.parse_args()

    if args.event:
        pr = json.loads(Path(args.event).read_text(encoding="utf-8"))["pull_request"]
        title, body = pr["title"], pr.get("body") or ""
    else:
        title = args.title or ""
        body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
    files = args.files if args.files is not None else (changed_files(args.base) if args.base else [])

    problems = check(title, body, files)
    impact = site_impact(files)
    print(f"site: {impact}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Site impact: `site:{impact}`\n\n")
            handle.write("Touches what the public image is built from: GHCR rebuilds on merge; "
                         "production is a separate release by the maintainer.\n"
                         if impact != "none" else
                         "Nothing the image is built from: merge when CI is green.\n")
    if args.label_file:
        Path(args.label_file).write_text(f"site:{impact}\n", encoding="utf-8")
    for problem in problems:
        print(f"PR: {problem}")
    if problems:
        print(f"\n{len(problems)} problem(s). Templates: .github/PULL_REQUEST_TEMPLATE/")
        return 1
    print(f"PR description OK ({len(files)} changed file(s), "
          f"{len(material_dirs(files))} topic(s) of material).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
