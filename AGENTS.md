# AGENTS.md

Global instructions for coding tasks. Repository-local instructions and established
project conventions take precedence.

## Scope

These workflow rules apply when modifying tracked repository files. Read-only
inspection, research, and review do not require an issue or branch.

## Workflow

### Scout

Before making tracked changes:

1. Inspect the repository status, current branch, relevant documentation, and tests.
2. In a GitHub repository, find the relevant issue with `gh issue list` and
   `gh issue view`. Create an issue if none exists.
3. In a repository without GitHub, record the task in `tasks.md`.
4. Present an implementation plan and wait for approval.

Do not modify tracked files, create a branch, commit, or open a PR during scouting.

### Implement

After the plan is approved:

1. Create a branch from `main` or the repository's integration branch:
   `agent/<issue-number>-<short-slug>`.
2. If no issue system exists, use `agent/<date>-<short-slug>`.
3. Implement and test the requested change.
4. Update the issue, or mark the `tasks.md` entry `[DONE]` with the completion date.
5. Commit, push, and open a PR.

Never commit directly to `main`.

Keep one issue, one branch, and one active PR per agent session. Do not begin a
second issue until the current work is committed and its PR is open.

Each simultaneous agent session must use a different branch.

Never create, use, or switch to a Git worktree unless the user explicitly requests
a worktree for the current task.

## GitHub

Use `gh` for GitHub issues, PRs, and projects. Do not add AI branding, assistant
signatures, or co-author trailers.

Use SSH for GitHub repository operations. Clone with an SSH URL and configure
GitHub remotes as `git@github.com:<owner>/<repository>.git`. Do not use HTTPS
Git remotes unless explicitly requested.

Use these project owners:

- CarlsbergGBS repositories: `--owner CarlsbergGBS`
- peterbb148 repositories: `--owner peterbb148`

Useful commands:

- `gh project list --owner OWNER`
- `gh project item-list NUMBER --owner OWNER`
- `gh project item-add NUMBER --owner OWNER --url ISSUE_URL`
- `gh project item-edit NUMBER --owner OWNER --url ISSUE_URL --field Status --value "In Progress"`

## Quality Requirements for GitHub Repositories

Before completing a pull request:

- Request a GitHub Copilot review after creating the pull request. Run
  `gh pr edit PR-NUMBER --add-reviewer @copilot`. Passing `@copilot` to
  `gh pr create --reviewer` can fail with a reviewer lookup error.
- Ensure test coverage for all new code is greater than 80%.
- Run the repository's configured test and coverage commands and report the results.
- Do not claim the coverage requirement passed unless it was measured successfully.

## Implementation Principles

- Follow repository-local conventions and tooling.
- Implement only the requested scope; avoid speculative features and complexity.
- Do not invent fallbacks, degraded modes, heuristic substitutes, or placeholder
  success paths.
- If a required provider, LLM, or dependency fails, return a clear failure.
- Add a fallback only when explicitly required, and document it in code and tests.

## Python

Always use UV for Python package and environment management. Do not use `pip`,
Poetry, Pipenv, Conda, or another Python package manager unless the user explicitly
requests it.

- Run commands with `uv run`.
- Add and remove dependencies with `uv add` and `uv remove`.
- Install and synchronize dependencies with `uv sync`.
- Follow configured formatters and linters. Otherwise use four-space indentation,
  a 100-character line limit, type hints, and standard import grouping.
- Catch specific exceptions only when the code can handle them meaningfully.
- Add Google-style docstrings to public or non-obvious functions and classes.
