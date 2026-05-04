# Release Workflow — dot_swarm

The canonical, end-to-end procedure for cutting a new dot_swarm release.
This file is the source of truth; the README and CHANGELOG describe what
*was* released, this file describes how to release the *next* one.

---

## What "release" means here

A dot_swarm release is three artefacts that must stay in lockstep:

| Artefact | Where it lives | Who consumes it |
|----------|----------------|-----------------|
| Source tarball + wheel on PyPI | https://pypi.org/project/dot-swarm/ | `pip install dot-swarm` |
| Tagged commit + GitHub Release notes | https://github.com/oasis-main/dot_swarm/releases | source readers, vendors, reproducible builds |
| Homebrew formula `dot-swarm.rb` | this repo (`/dot-swarm.rb`); shipped tap copy | `brew install dot-swarm` (when tap is published) |

If any of those drift the release is broken — a user who runs `brew
upgrade dot-swarm` and gets a different version than `pip install -U
dot-swarm` will not trust the project. The procedure below is designed
to keep all three locked together.

---

## Pre-flight checklist (do all of these before tagging)

1. **Working tree is clean on `main`.** `git status` shows no
   modifications. Any in-flight work either lands or gets stashed.
2. **Full test suite green inside the project venv.** Per project
   memory we never run bare `python3`:
   ```bash
   source .venv/bin/activate
   python -m pytest tests/
   ```
   The expected count for v1.0 is 231 passed, 3 skipped. A failing
   test blocks the release — never publish on red.
3. **Version bumped in both places that ship.** They must agree:
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `src/dot_swarm/cli.py` → `@click.version_option("X.Y.Z")`
   The `swarm --version` CLI is what users will check first; if it
   disagrees with PyPI metadata, support pain follows.
4. **CHANGELOG.md has an entry for the new version**, dated, with the
   Added / Changed / Removed sections users actually care about.
   Released entries are append-only — never rewrite past entries.
5. **The .swarm/queue.md is current.** Items shipped in this release
   are marked DONE with a completion timestamp. SWC-046-style
   multi-phase items keep their entry but record which phase landed.
6. **`python -m build` succeeds locally** and produces both
   `dist/dot_swarm-X.Y.Z-py3-none-any.whl` and
   `dist/dot_swarm-X.Y.Z.tar.gz`. Delete `dist/` afterwards so it
   doesn't accidentally get committed.

If any pre-flight fails, fix-then-restart — do not partial-release.

---

## Cut the release

### 1. Commit + push `main`

Bundle the version bump, CHANGELOG, and any release-related doc edits
into a single commit. The pattern that has worked:

```bash
git add pyproject.toml src/dot_swarm/cli.py CHANGELOG.md docs/ \
        src/dot_swarm/<new modules> tests/<new tests>
git commit -m "feat: vX.Y.Z — <one-line summary>

<bullet list of headline changes>

Co-Authored-By: <tooling co-author if applicable>"
git push origin main
```

`.swarm/` is gitignored by default (trail-invisible), so any updates
to `.swarm/queue.md` or `.swarm/workflows/release.md` only land on
local disk. Run `swarm trail visible` and re-stage if you want the
trail in the commit.

### 2. Tag and push the tag — this triggers PyPI publish

```bash
git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>

<longer notes from CHANGELOG.md>"
git push origin vX.Y.Z
```

Pushing a `v*` tag fires `.github/workflows/publish-pypi.yml`. The
workflow uses **Trusted Publishing (OIDC)** — no API token, no secret
in the repo. The PyPI side requires:

- A configured Trusted Publisher at
  https://pypi.org/manage/project/dot-swarm/settings/publishing/ with:
  - Repository: `oasis-main/dot_swarm`
  - Workflow: `publish-pypi.yml`
  - **Environment name: `release`** (must match the workflow's
    `environment: release` field exactly — mismatched names produce
    `invalid-publisher` errors with no useful debug output).
- A GitHub Environment named `release` on the repo. Settings →
  Environments → New environment → `release`. Empty config is fine.

If either side is misconfigured the workflow fails at the publish
step. The fix is to align both, then re-push the tag (`git push
--force origin vX.Y.Z` after `git tag -d vX.Y.Z` and re-create) — or,
preferred, cut a new patch tag rather than rewrite history.

### 3. Watch the workflow to completion

```bash
gh run list --workflow=publish-pypi.yml --limit 3
gh run watch <run-id> --exit-status
```

Expected completion: ~30 seconds. All steps green is the only
acceptable outcome. A failure here means the tag exists on GitHub but
nothing landed on PyPI; investigate, fix, re-tag (next patch).

### 4. Verify on PyPI

```bash
curl -s https://pypi.org/pypi/dot-swarm/json | \
  python3 -c "import sys, json; d=json.load(sys.stdin); \
              print(d['info']['version'])"
```

Should print `X.Y.Z`. Also do one round-trip install:

```bash
pip install --dry-run dot-swarm==X.Y.Z
```

Resolves cleanly = release is real.

---

## Update the Homebrew formula

This is **SWC-005** in `.swarm/queue.md`. Skipping it is fine for an
internal pre-release, but every public release must include it or
brew users get stale code.

### 1. Compute the new tarball SHA

```bash
curl -sL "https://files.pythonhosted.org/packages/source/d/dot-swarm/dot_swarm-X.Y.Z.tar.gz" \
  -o /tmp/dot_swarm-X.Y.Z.tar.gz
shasum -a 256 /tmp/dot_swarm-X.Y.Z.tar.gz
```

### 2. Regenerate transitive resource blocks

`homebrew-pypi-poet` is the canonical tool but it's broken on Python
≥ 3.12 (depends on removed `pkg_resources`). The reliable path is
pip's own `--report` output (works on Python 3.11+):

```bash
python3 -m venv /tmp/poet_env
/tmp/poet_env/bin/pip install --dry-run --quiet --report /tmp/install_report.json \
    --ignore-installed "dot-swarm[crypto]==X.Y.Z"
```

Then a small script walks `install_report.json`, queries PyPI's JSON
API for each dep's sdist URL + sha256, and emits Ruby `resource`
blocks. The script lives in this workflow's git history; the relevant
commit is the v1.0.0 release. Re-run it for every new release.

### 3. Update `dot-swarm.rb` in this repo

- Bump `url`, `sha256`, and the version string in the test block
- Replace the resource block list wholesale (do not try to
  hand-merge — pinned versions drift across releases)
- Verify with `ruby -c dot-swarm.rb` (Ruby syntax check; passes
  before any actual Homebrew check)

### 4. Push the formula update to the tap

The tap repo lives at **[oasis-main/homebrew-dot-swarm](https://github.com/oasis-main/homebrew-dot-swarm)**
and is structured as a standard Homebrew tap (`Formula/dot-swarm.rb`,
`brew test-bot` CI matrix, MIT LICENSE). The release-time procedure:

```bash
TAP=~/Documents/Runes/homebrew-dot-swarm
cp dot-swarm.rb "$TAP/Formula/dot-swarm.rb"
git -C "$TAP" add Formula/dot-swarm.rb
git -C "$TAP" commit -m "dot-swarm: vX.Y.Z"
git -C "$TAP" tag -a vX.Y.Z -m "Tap snapshot for dot_swarm vX.Y.Z"
git -C "$TAP" push origin main vX.Y.Z
```

Pushing to `main` triggers `.github/workflows/tests.yml` on the tap
(`brew style` + `brew test-bot` across `macos-14`, `macos-13`,
`ubuntu-latest`). All three must pass before the tag is considered
shipped.

The decision to use a project-owned tap rather than `homebrew-core`
is recorded in [SWC-006]: the project's release cadence and the
resource-pinning churn make the wait for homebrew-core review
disproportionate. Re-evaluate once the v1.x line stabilizes.

### 5. Verify the formula installs

From a clean shell on macOS:

```bash
brew install --build-from-source <tap>/dot-swarm
swarm --version    # must print X.Y.Z
swarm init --visible
swarm add "smoke test"
```

If brew install produces compilation errors for `cryptography`,
`pydantic-core`, or `rpds-py`, the cause is almost always that the
sdist needs Rust at build time. The formula already declares
`depends_on "rust" => :build` for that reason; if a future release
adds another Rust-built dep, the same line covers it.

---

## Post-release housekeeping

1. **Update the `.swarm/queue.md`** — mark SWC-004 (PyPI publish),
   SWC-005 (Homebrew bump), SWC-006 (tap submission, if applicable)
   DONE with the timestamp.
2. **Open a GitHub Release** for the tag. Body = the matching
   CHANGELOG.md section. The release page is what most users land on
   when they Google for the version.
3. **Drop `.swarm_key.old` in any swarm that rotated keys** during the
   pre-release verification. Leftover old keys are an attack surface
   and a long-term maintenance smell.
4. **Schedule a 2-week follow-up** if the release exposed any deferred
   work — this is what `swarm schedule` and the `/loop` tooling
   exist for. The pattern: a one-time agent in 14 days that checks
   "did we actually ship the homebrew-core PR" or "have we removed
   the v1.0 migration shim yet."
5. **Bump `[Unreleased]` section in CHANGELOG.md** to start collecting
   the next release's changes. Even an empty header is a useful
   signal that the project is open for new work.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Workflow fails with `invalid-publisher` | PyPI Trusted Publisher environment name doesn't match the workflow's `environment:` value | Align both to `release` (or the same string), re-tag |
| Workflow fails before publish step | Missing GitHub Environment named `release` on the repo | Settings → Environments → New `release` |
| `pip install` resolves but `swarm --version` prints the old version | `pyproject.toml` and `cli.py` disagreed; pip got the new metadata but ships the old code in some cached editable install | Reinstall `pip install --force-reinstall dot-swarm==X.Y.Z`; in dev, `pip install -e .` after every version edit |
| Brew install fails on `cryptography` build | Missing Rust at build time on the user's machine (or the formula forgot `depends_on "rust" => :build`) | Add the rust build dep in the formula; do a fresh `brew install --build-from-source` to verify |
| Tag pushed but no GH Actions run started | Workflow file has an `on:` mismatch (e.g. `tags: [v*]` vs `tags: ['v*']` quoting) or the workflow file doesn't exist on the tag's commit | Verify the workflow exists on the tagged sha, fix on `main`, re-tag |
| `swarm migrate` reports no changes on a 0.3.x layout | The user already ran migrate in a previous session | Expected — migrate is idempotent. Confirm by checking that `claims/`, `federation/strangers/`, and `.gitignore` already match the v1.0 layout |

---

## Phase rollouts (multi-version features)

Some features ship across multiple releases — SWC-046 (the swarm key)
is the canonical example: Phase 1 in v1.0, Phase 2 (auto-encrypted
memory.md/state.md) and Phase 3 (federation key exchange) in later
releases.

The discipline:

- Each phase's CHANGELOG entry is **its own dated section**, not a
  retroactive edit to the prior entry.
- The queue.md item stays OPEN with a `Phase N done` annotation in
  brackets next to its state until every phase is shipped.
- Migration code (`src/dot_swarm/migrate.py`) accumulates a check for
  each phase. Migration must remain idempotent across phase
  boundaries — running `swarm migrate` against a v1.2 directory from
  v1.0 must end up at the v1.2 layout regardless of starting point.
- The release commit message names which phase landed, not just the
  feature.

---

## What this document is NOT

- A substitute for reading `.github/workflows/publish-pypi.yml`. The
  workflow is the source of truth for what runs on a tag push; if
  this document and that file disagree, the workflow wins.
- A substitute for human review. Every release ships with a 30-second
  human pause to confirm: tests green, version bumped both places,
  CHANGELOG written, and tag message ready. Skipping the pause is how
  bad versions go to PyPI.
- A description of the *protocol* — that lives in
  `docs/ARCHITECTURE.md`. This file is purely about packaging and
  distribution.
