"""Verify the CI binary allowlist against real Git diffs."""

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def git(repo: Path, *args: str) -> str:
    """Run Git in a temporary repository."""
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def commit_file(repo: Path, filename: str) -> str:
    """Modify one path and return the new commit SHA."""
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    original = path.read_text() if path.exists() else ""
    path.write_text(original + "changed\n")
    git(repo, "add", "--", filename)
    git(repo, "commit", "-m", f"Change {filename}")
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a repo with an initial commit for push and PR comparisons."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "CI test")
    git(tmp_path, "config", "user.email", "ci@example.invalid")
    commit_file(tmp_path, "README.md")
    return tmp_path


def detector(repo: Path, event: str, base: str, head: str) -> subprocess.CompletedProcess[str]:
    """Run the same detector that GitHub Actions uses."""
    return subprocess.run(
        ["bash", str(ROOT / "scripts/cli_changed.sh"), event, base, head],
        cwd=repo,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("event", ["pull_request", "push"])
@pytest.mark.parametrize(
    ("path", "build"),
    [
        ("docs/CLI.md", "false"),
        ("config/vertical.yaml", "false"),
        ("src/twinkly_wall/config.py", "false"),
        ("src/twinkly_wall/cards/torch_vertical.py", "false"),
        ("src/twinkly_wall/cards/__init__.py", "false"),
        ("assets/logo.png", "false"),
        ("src/twinkly_wall/command.py", "true"),
        ("src/twinkly_wall/cli.py", "true"),
        ("src/twinkly_wall/daemon.py", "true"),
    ],
)
def test_binary_scope(repo: Path, event: str, path: str, build: str) -> None:
    base = git(repo, "rev-parse", "HEAD")
    head = commit_file(repo, path)
    result = detector(repo, event, base, head)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == build


def test_pr_ignores_cli_changes_only_on_base(repo: Path) -> None:
    git(repo, "switch", "-c", "feature")
    head = commit_file(repo, "docs/CLI.md")
    git(repo, "switch", "main")
    base = commit_file(repo, "src/twinkly_wall/cli.py")
    assert detector(repo, "pull_request", base, head).stdout.strip() == "false"


def test_mixed_push_detects_cli_change_across_commits(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/twinkly_wall/cli.py")
    head = commit_file(repo, "src/twinkly_wall/cards/torch_vertical.py")
    assert detector(repo, "push", base, head).stdout.strip() == "true"


def test_missing_revision_fails_the_gate(repo: Path) -> None:
    result = detector(repo, "push", "invalid-ref", "HEAD")
    assert result.returncode != 0
    assert not result.stdout


def test_release_uses_explicit_binary_build_input() -> None:
    workflows = ROOT / ".github/workflows"
    release = yaml.load((workflows / "release.yml").read_text(), Loader=yaml.BaseLoader)
    ci = yaml.load((workflows / "ci.yml").read_text(), Loader=yaml.BaseLoader)
    validate = release["jobs"]["validate"]
    assert release["on"]["push"]["tags"] == ["v*"]
    assert validate["uses"] == "./.github/workflows/ci.yml"
    assert validate["with"]["build-binaries"] == "true"
    assert ci["on"]["workflow_call"]["inputs"]["build-binaries"]["type"] == "boolean"
    assert release["jobs"]["publish"]["needs"] == "validate"


@pytest.mark.parametrize(
    ("build", "overrides", "expected_error"),
    [
        ("false", {}, ""),
        ("true", {}, ""),
        ("false", {"SCOPE_RESULT": "failure"}, "Binary scope or tests did not pass"),
        ("true", {"TEST_RESULT": "failure"}, "Binary scope or tests did not pass"),
        ("", {}, "Binary scope did not report"),
        ("true", {"MACOS_BUILD": "skipped"}, "macos-binary returned skipped"),
        ("true", {"UBUNTU_INSTALL": "failure"}, "ubuntu-install returned failure"),
        ("true", {"RASPBERRY_PI": "cancelled"}, "raspberry-pi-binary returned cancelled"),
        ("false", {"MACOS_INSTALL": "success"}, "macos-install returned success"),
    ],
)
def test_required_ci_gate(build: str, overrides: dict[str, str], expected_error: str) -> None:
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    script = ci["jobs"]["required-ci"]["steps"][0]["run"]
    binary_result = "success" if build == "true" else "skipped"
    results = {
        "SCOPE_RESULT": "success",
        "TEST_RESULT": "success",
        "BUILD_BINARIES": build,
        "MACOS_BUILD": binary_result,
        "MACOS_INSTALL": binary_result,
        "UBUNTU_BUILD": binary_result,
        "UBUNTU_INSTALL": binary_result,
        "RASPBERRY_PI": binary_result,
    }
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        env=results | overrides,
        capture_output=True,
        text=True,
    )

    assert result.returncode == (1 if expected_error else 0), result.stdout + result.stderr
    if expected_error:
        assert expected_error in result.stdout
