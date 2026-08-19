# Beta Sync Plan (Model B): ha-addons-beta → ha-addons

**Direction reversed as of 2026-06-20.** This repo (`ha-addons-beta`) is now the
**source of truth**. You author and test the LibreCoach add-on here, then mirror the
shared addon source **up** into the prod `ha-addons` repo for release.

> Earlier cycles synced prod → beta (Model A). That is retired. Do **not** author the
> add-on in prod anymore — prod's `librecoach/` is a downstream mirror of beta's.

**Current production baseline: `1.5.1` (2026-08-08).** Production carries Node-RED ref
`9decb68af111a67f8ba552719a747e0e8fdf603a`. Prod sets its own `version:` and `image:`
(beta is `…-librecoach-beta`); bump prod's version above `1.5.1` for the next release.

## Roles

| Repo | Path | Role |
|---|---|---|
| `ha-addons-beta` | `/home/ted/src/librecoach/ha-addons-beta` | **Source of truth.** All authoring + ALL verification happen here. |
| `ha-addons` | `/home/ted/src/librecoach/ha-addons` | Prod. Receives the mirror directly on `main`; committing/pushing `main` = release. |

Both repos are **separate GitHub repos with no shared git history** (HA add-on
repositories are consumed by URL; beta testers add the beta URL). They are kept tied
only by the file mirror below — never by a git merge across them.

### Branch conventions

- **Prod** uses `main` as the migration target. Do not create a release/integration branch for
  the beta-to-prod mirror.
- **Beta** branch names vary per testing cycle.
- `mirror.sh` reads both branch names live for reporting, but before applying the mirror,
  prod must be checked out on `main`.

## Release flow

1. Author + test in `ha-addons-beta` on the beta branch for this cycle. Commit there.
   Push beta → beta build → verify in HA.
2. Ensure prod is checked out on `main`, then run `beta-notes/mirror.sh --apply` to copy the
   addon source into prod.
3. In prod: apply any flagged `config.yaml` deltas, run tests, and review the pending changes
   on `main`.
4. **Release = commit and push prod `main` in `ha-addons`.** This triggers the prod build and
   is the step that reaches end users. **Never do it without explicit approval.** Bump prod's
   `version:` at this point.

> **The mirror copies files, not git history.** The two repos share no history, so beta's
> commits never cross over. Each migration lands in prod as **one fresh commit** (or however
> many you choose to split it into) — the granular beta commit history stays in beta.

---

## CRITICAL: Node-RED is an upstream build dependency — handle it FIRST

The add-on `Dockerfile` fetches the exact `librecoach-node-red` commit recorded in
`librecoach/node-red.ref` and `RUN`-asserts `artifact/flows.json` exists. The pointer is part of
the mirrored add-on source, so beta and prod build the same Node-RED revision. `mirror.sh` does
not copy the Node-RED repository itself. The fetch is anonymous, which requires
`librecoach-node-red` to stay public.

Only the files the add-on consumes at runtime are bundled: `artifact/flows.json`,
`flows_cred.json`, `package.json`, `data/`, and `LICENSE`. Adding a new runtime dependency on
another path in the Node-RED repo means adding it to the allowlist in the `Dockerfile`.

Therefore, before you test in beta or release to prod:

1. **`artifact/flows.json` must be rebuilt** whenever `src/` changes. The flow-splitter plugin
   rebuilds it when the Node-RED add-on restarts; a Deploy alone does not rebuild it, and the
   wiring-map tool never writes it. If `src/` is edited directly, the artifact goes stale and
   the build bundles old flows. Gate:
   `git log -1 --format=%ci -- artifact/` must be **≥** `git log -1 --format=%ci -- src/`.
2. **Merge the node-red feature branch → `main` and push it first.** Then run
   `beta-notes/update-node-red-ref.sh [full-commit-sha]`. The script requires a clean Node-RED
   working tree, fetches `origin/main`, verifies the commit and required flow files, checks that
   `artifact/` is not older than `src/`, and updates the tracked pointer. Pushing node-red `main`
   alone triggers no user-facing build.
3. Commit the changed `librecoach/node-red.ref` with the corresponding add-on work. Changing the
   pointer invalidates the Docker layer; the image retains the pointer at
   `/opt/librecoach-project/.librecoach-node-red-ref` for traceability.
4. Node-RED edits are done in a throwaway sandbox, then synced back to
   `/home/ted/src/librecoach/librecoach-node-red` via `rsync -a --delete --exclude='.git/'`
   (sandbox → canonical). Never blind-copy a sandbox based on `main` over a feature branch.
   Apply only the delta as a 3-way patch (`git apply --3way`) if needed.

---

## What gets mirrored

**Synced surface: `librecoach/` only, minus `config.yaml`.** That is the entire shared
add-on payload (`run.sh`, `Dockerfile`, `rootfs/`, `translations/`, `vehicle_bridge/`,
`librecoach_ble/`, `CHANGELOG.md`, `DOCS.md`, brand assets, …). Everything outside
`librecoach/` is intentionally repo-specific and is **never** synced:

| Excluded | Why it must stay prod-specific |
|---|---|
| `librecoach/config.yaml` | prod's `version:` + `image: …-librecoach` (beta is `…-librecoach-beta`) |
| `repository.json` | beta "BETA TESTING" name + beta URL |
| `README.md` (root) | beta landing page warns testers off prod |
| `.github/*` | beta workflow carries `SUFFIX: beta` |
| `beta-notes/*` | beta-only working notes (this file lives here) |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | identical today, but kept repo-local on principle |

`mirror.sh` scopes rsync to `librecoach/`, so it physically cannot touch prod's root,
`.github/`, `.git/`, dev tooling, or beta notes — even with `--delete`.

### Line endings

All add-on source (including `librecoach/LICENSE` and `librecoach/CONTRIBUTING.md`) is LF
in both repos; prod's historical CRLF was normalized to LF in an earlier release. Keep beta
canonical at LF so the mirror stays a clean content sync.

---

## Using mirror.sh

```bash
beta-notes/mirror.sh            # DRY RUN — shows real content changes, writes nothing
beta-notes/mirror.sh --apply    # mirror beta/librecoach → prod/librecoach
```

- Uses `--checksum`, so the itemized list shows **content** changes only (`>fc...`).
  `.f..t` lines are mtime-only and never reach git.
- `--delete` removes files from prod's `librecoach/` that no longer exist in beta's, so
  code cleanups/removals propagate (this is why Model B does a *perfect* sync — you verify
  in beta, then prod follows exactly).
- After mirroring it runs a **config.yaml drift check**: prod vs beta `config.yaml` must
  differ on `version:` / `image:` only. Anything else flagged is a real option/schema change
  you must port to prod by hand (see below).

## Pending config hand-ports

None. The drift check is clean — prod vs beta `config.yaml` differ on `version:` /
`image:` only.

When you next change `options:`/`schema:` in beta, record the required prod hand-port
here so the next release picks it up, then clear this section once applied.

---

## config.yaml (Option A — excluded, hand-ported)

`config.yaml` is never copied. When you change `options:`/`schema:` in beta (e.g. a new
feature toggle like `hughes_enabled`), apply the **same** edits to prod's `config.yaml`,
keeping prod's `version:` and `image:` lines. The mirror's drift check will nag you until the
only remaining differences are those two lines. Verify with pure Python (bypasses the `rtk`
hook, which mangles `diff`):

```bash
python3 - <<'EOF'
import difflib
a=open('/home/ted/src/librecoach/ha-addons/librecoach/config.yaml').read().splitlines()
b=open('/home/ted/src/librecoach/ha-addons-beta/librecoach/config.yaml').read().splitlines()
print('\n'.join(l for l in difflib.unified_diff(a,b) if l[:1] in '+-' and l[:2] not in ('++','--')))
EOF
```

---

## Preparing the changelog

The add-on changelog must cover **both** the files mirrored from `ha-addons-beta/librecoach/`
and the Node-RED project revision referenced by `librecoach/node-red.ref`. Do this before
asking for release review.

1. Identify the Node-RED range that prod users will receive. The old ref is the value currently
   committed in prod `main`; the new ref is the value from beta:

   ```bash
   OLD_NR_REF=$(git -C /home/ted/src/librecoach/ha-addons show main:librecoach/node-red.ref)
   NEW_NR_REF=$(cat /home/ted/src/librecoach/ha-addons-beta/librecoach/node-red.ref)
   ```

   If prod has already been mirrored locally, `git show main:...` still reads the committed
   prod baseline, while the working tree contains the pending release ref.

2. Review every Node-RED commit and changed source file in that range:

   ```bash
   git -C /home/ted/src/librecoach/librecoach-node-red log --oneline --decorate "$OLD_NR_REF..$NEW_NR_REF"
   git -C /home/ted/src/librecoach/librecoach-node-red diff --stat "$OLD_NR_REF..$NEW_NR_REF" -- src artifact package.json
   git -C /home/ted/src/librecoach/librecoach-node-red diff "$OLD_NR_REF..$NEW_NR_REF" -- src
   ```

   Use commit bodies for intent, but verify against the source diff. Release notes should be
   user-facing: new entities, changed behavior, fixed integrations, migration behavior, and
   compatibility fixes. Do not list internal artifact churn unless it affects users.

3. Review add-on repo changes outside Node-RED:

   ```bash
   rtk proxy git -C /home/ted/src/librecoach/ha-addons-beta diff origin/main...HEAD -- librecoach
   rtk proxy git -C /home/ted/src/librecoach/ha-addons diff -- librecoach
   ```

   The beta diff shows authored add-on work before mirroring; the prod diff shows the exact
   pending release payload after mirroring. Include changes to startup scripts, BLE handlers,
   translations, docs, migrations, and tests when they represent customer-visible behavior.

4. Update `ha-addons-beta/librecoach/CHANGELOG.md` first, then run
   `beta-notes/mirror.sh --apply` so prod receives the same changelog entry. Re-read the top
   changelog section in prod after mirroring.

---

## GitHub Releases

Both repos (`ha-addons-beta` and `ha-addons`) use LibreCoach-scoped release tags (e.g. `librecoach/1.5.0`). Create a matching release in **both repos** whenever a new version ships to prod.

> **Reminder:** After completing the pre-release checklist and pushing prod `main`, create GitHub Releases tagged `librecoach/<version>` in both `ha-addons-beta` and `ha-addons`. Use the CHANGELOG entry for that version as the release body.

---

## Pre-release checklist (before committing/pushing prod main)

- [ ] All verification done in **beta** and the beta build tested in HA
- [ ] **Node-RED `main` merged + pushed** with a fresh `artifact/flows.json`, and
      `librecoach/node-red.ref` updated to that commit (see CRITICAL)
- [ ] `CHANGELOG.md` updated from both the add-on diff and the full Node-RED
      `OLD_NR_REF..NEW_NR_REF` range
- [ ] Prod checked out on `main`
- [ ] `mirror.sh --apply` run; prod `git status` shows only intended changes
- [ ] config.yaml drift check is clean (only `version:` + `image:` differ); image still ends `-librecoach`
- [ ] `translations/es.yaml` keys match `translations/en.yaml` (mirror.sh checks this — es.yaml must always mirror en.yaml's options)
- [ ] Add-on tests pass in prod: `(cd librecoach/librecoach_ble/tests && python3 -m pytest -q)`
- [ ] prod `version:` bumped for the release
- [ ] `rtk proxy git diff` reviewed (the `rtk` hook rewrites plain `git diff` into a non-patch summary)
- [ ] Explicit approval obtained for committing/pushing prod `main`

> **Tooling caveat:** the `rtk` hook rewrites `git diff`/`diff`/`sha256sum` output into summaries
> that are **not** reliable for byte comparisons or patches. Use `rtk proxy git diff` for real
> diffs/patches, and pure Python (`hashlib`/`difflib`) for authoritative content comparisons.
