# Repository rulesets

This directory contains repository rules as code.

## `main.json`

Branch protection for `main`:

- **Target**: branch `main` only.
- **Enforcement**: active.
- **Rules**:
  - Block branch deletion.
  - Block force pushes (`non_fast_forward`).
  - Require linear history.
  - Require a pull request before merging.
  - Require conversation resolution before merging.
  - Require the `test (ubuntu-latest, 3.12)` and
    `test (windows-latest, 3.12)` status checks to pass.
  - Allow only `squash` merges.
  - Do **not** require a specific number of approvals — the
    project has a solo maintainer.

## Importing the ruleset

The ruleset is **not** auto-applied. Import it once through the
GitHub web UI:

1. Open `Repository settings → Rules → Rulesets → New ruleset`.
2. Click **Import** and point at
   `.github/rulesets/main.json` in this repository.
3. Verify the imported rules match what the file describes.
4. Click **Create**.

After the first CI run on `main` lands, double-check the
status-check context names against a real Actions run. If
GitHub generates different names (for example, it may produce
`ci / test (ubuntu-latest, 3.12)` with a `/` prefix or
different OS label), update `main.json` to match and re-import.

## Modifying the policy

Edit `main.json`, push, then re-import via the web UI. Rules
defined here are documentation of intent; the actual policy
is whatever GitHub currently has applied.
