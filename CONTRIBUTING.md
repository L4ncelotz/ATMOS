# Contributing to ATMOS

ATMOS — by Estellez

Thanks for your interest. The project keeps its contribution
surface small on purpose. Read this end-to-end before opening an
issue or a pull request.

## Before you start

- Search the issue tracker. Someone may have already reported
  the same thing or started a related discussion.
- If the change is non-trivial (anything beyond a typo, a small
  bug fix, or a single-scene tweak), **open an issue first** so
  the approach can be discussed before code lands.
- Read [`README.md`](./README.md) and the source layout. The
  architecture rule is: external provider responses never reach
  the renderer directly; they are normalized into `WeatherState`
  first.

## Workflow

1. Fork the repository.
2. Create a topic branch from `main`:
   ```bash
   git checkout -b fix/<short-description>
   ```
3. Make your changes in small, focused commits.
4. Run the test suite and the binary build before opening a PR:
   ```bash
   pip install -e ".[dev,build]"
   pytest
   python build.py
   ./dist/atmos.exe --version
   ```
5. Push your branch and open a pull request against `main`.

## Coding conventions

- Python 3.12+ only. Type hints on every public function.
- Keep the renderer provider-independent. New weather sources
  must arrive as a `WeatherProvider` plus a `mapper.py` extension;
  do not leak Open-Meteo specifics into the scene code.
- Particle / cloud / wind visuals are owned by the `scenes/`
  modules. New weather effects belong there, not in `engine/`.
- Avoid new dependencies. Each one is a long-term maintenance
  cost. If you need one, justify it in the PR.

## Commit messages

- Imperative mood: "Add `FogScene`" not "Added fog".
- Reference the issue or PR number when relevant: `(#42)`.
- One logical change per commit.

## Pull request checklist

- [ ] `pytest` passes locally
- [ ] `python build.py` produces a working `dist/atmos.exe` that prints `atmos --version`
- [ ] No new dependencies without justification in the PR body
- [ ] New behavior is covered by a test in `tests/`
- [ ] `README.md` and `CHANGELOG.md` updated if the user-visible
      behavior changed
- [ ] No secrets, no local paths, no generated build artifacts in
      the diff

## Code of conduct

Be kind. Critique ideas, not people. The project is small and the
maintainer reads every PR; thoughtful discussion is welcome,
hostility is not.
