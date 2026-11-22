"""Verify binary retention decisions and destructive API boundaries."""

import json
import subprocess
from unittest.mock import MagicMock

import pytest

from scripts import retain_binaries as retention


def release(number, *, draft=False):
    version = f"0.{number}.0"
    archive = f"twinkly-cli-{version}-darwin-arm64.tar.gz"
    return {
        "tag_name": f"v{version}",
        "draft": draft,
        "published_at": f"2026-10-{number:02d}T00:00:00Z",
        "assets": [
            {"id": number * 10, "name": archive},
            {"id": number * 10 + 1, "name": archive + ".sha256"},
            {"id": number * 10 + 2, "name": "unrelated.zip"},
        ],
    }


def ubuntu_assets(number):
    version = f"0.{number}.0"
    archive = f"twinkly-cli-{version}-ubuntu-arm64.tar.gz"
    base_id = number * 10 + 3
    return [{"id": base_id, "name": archive}, {"id": base_id + 1, "name": archive + ".sha256"}]


def current_release(number):
    record = release(number)
    record["assets"].extend(ubuntu_assets(number))
    return record


def artifact(number, version, *, run=None, expired=False, target=("twinkly-cli", "darwin-arm64")):
    command, platform = target
    return {
        "id": number,
        "name": f"{command}-{version}-{platform}",
        "workflow_run": {"id": run or number},
        "expired": expired,
        "created_at": f"2026-10-{number:02d}T00:00:00Z",
    }


def current_artifacts(number, version):
    return [
        artifact(number + 10 * index, version, run=number, target=target)
        for index, target in enumerate(retention.CURRENT_TARGETS)
    ]


def success_runs(*numbers):
    return {number: {"status": "completed", "conclusion": "success"} for number in numbers}


@pytest.mark.parametrize("count,deleted", [(1, []), (2, []), (3, [10, 11]), (4, [20, 21, 10, 11])])
def test_release_history_preserves_current_previous_and_unrelated_assets(count, deleted):
    releases = [release(n) for n in range(1, count)] + [current_release(count)]
    assert retention.release_deletions(releases, f"v0.{count}.0") == deleted


def test_drafts_and_releases_without_binaries_do_not_displace_previous_version():
    records = [release(1), current_release(2), release(3, draft=True), release(4)]
    records[-1]["assets"] = [{"id": 99, "name": "manual.pdf"}]
    assert retention.release_deletions(records, "v0.2.0") == []


@pytest.mark.parametrize("records", [[], [release(1)], [release(3, draft=True)]])
def test_missing_current_release_blocks_all_deletions(records):
    with pytest.raises(ValueError, match="Current release"):
        retention.release_deletions(records, "v0.3.0")


def test_current_release_needs_binary_and_checksum():
    current = current_release(3)
    current["assets"] = current["assets"][:1]
    with pytest.raises(ValueError, match="archive and checksum"):
        retention.release_deletions([release(1), release(2), current], "v0.3.0")


def test_ci_keeps_distinct_versions_and_preserves_other_active_runs():
    records = [
        artifact(1, "0.1.0"),
        artifact(2, "0.2.0"),
        artifact(3, "0.2.0"),
        *current_artifacts(4, "0.3.0"),
        artifact(5, "0.4.0"),
        artifact(6, "0.5.0"),
        artifact(7, "0.6.0", expired=True),
    ]
    runs = success_runs(1, 2, 3, 4, 7)
    runs[5] = {"status": "in_progress", "conclusion": None}
    runs[6] = {"status": "completed", "conclusion": "failure"}
    assert retention.artifact_deletions(records, runs, 4) == [1, 2, 6]


def test_ci_legacy_and_unrelated_artifacts():
    legacy = artifact(1, "legacy")
    legacy["name"] = retention.LEGACY_ARTIFACT
    unrelated = artifact(2, "other")
    unrelated["name"] = "coverage-report"
    current = current_artifacts(3, "0.1.0")
    assert retention.artifact_deletions([legacy, unrelated, *current], success_runs(1), 3) == [1]


def test_only_newest_duplicate_build_is_retained():
    assert retention.artifact_deletions(
        [artifact(1, "0.1.0"), *current_artifacts(2, "0.1.0")], success_runs(1), 2
    ) == [1]


@pytest.mark.parametrize(
    "records", [[], [artifact(1, "0.1.0")], [artifact(2, "0.1.0", expired=True)]]
)
def test_ci_missing_current_artifact_blocks_deletions(records):
    with pytest.raises(ValueError, match="Current verified run"):
        retention.artifact_deletions(records, {}, 2)


def test_paginated_inventory(monkeypatch):
    api = MagicMock(
        side_effect=[
            [[release(1)], [release(2)]],
            [{"artifacts": [artifact(1, "0.1.0")]}, {"artifacts": []}],
        ]
    )
    monkeypatch.setattr(retention, "github_api", api)
    assert len(retention.inventory("owner/repo", "releases")) == 2
    assert len(retention.inventory("owner/repo", "artifacts")) == 1
    assert api.call_args.kwargs == {"paginate": True}


def test_api_has_no_shell_or_retry_and_propagates_failures(monkeypatch):
    run = MagicMock(return_value=subprocess.CompletedProcess([], 0, stdout='{"id": 1}'))
    monkeypatch.setattr(retention.subprocess, "run", run)
    assert retention.github_api("repos/owner/repo/releases", paginate=True) == {"id": 1}
    assert run.call_args.args[0][-2:] == ["--paginate", "--slurp"]
    assert run.call_args.kwargs["check"] is True
    run.return_value.stdout = ""
    assert retention.github_api("repos/owner/repo/releases/assets/1", delete=True) is None
    assert run.call_args.args[0][-2:] == ["--method", "DELETE"]
    run.side_effect = subprocess.CalledProcessError(1, ["gh"])
    with pytest.raises(subprocess.CalledProcessError):
        retention.github_api("repos/owner/repo/releases")


@pytest.mark.parametrize("apply", [False, True])
def test_release_cleanup_dry_run_and_verified_deletion(monkeypatch, apply):
    api = MagicMock()
    monkeypatch.setattr(retention, "github_api", api)
    read = MagicMock(
        side_effect=[[release(1), release(2), current_release(3)], [release(2), current_release(3)]]
    )
    monkeypatch.setattr(retention, "inventory", read)
    assert retention.prune("owner/repo", "releases", "v0.3.0", apply=apply) == [10, 11]
    assert api.call_count == (2 if apply else 0)
    assert read.call_count == (2 if apply else 1)
    if apply:
        assert api.call_args.args[0] == "repos/owner/repo/releases/assets/11"
        assert api.call_args.kwargs == {"delete": True}


def test_cleanup_verification_failure_is_visible(monkeypatch):
    monkeypatch.setattr(
        retention, "inventory", lambda *_: [release(1), release(2), current_release(3)]
    )
    monkeypatch.setattr(retention, "github_api", MagicMock())
    with pytest.raises(RuntimeError, match="could not be verified"):
        retention.prune("owner/repo", "releases", "v0.3.0", apply=True)


def test_ci_cleanup_only_queries_binary_runs_and_verifies_removal(monkeypatch):
    old = artifact(1, "0.1.0")
    current = current_artifacts(2, "0.1.0")
    unrelated = artifact(3, "other")
    unrelated["name"] = "coverage-report"
    monkeypatch.setattr(
        retention,
        "inventory",
        MagicMock(side_effect=[[old, *current, unrelated], [*current, unrelated]]),
    )
    api = MagicMock(return_value={"status": "completed", "conclusion": "success"})
    monkeypatch.setattr(retention, "github_api", api)
    assert retention.prune("owner/repo", "artifacts", "2", apply=True) == [1]
    assert api.call_count == 3
    assert api.call_args.args[0] == "repos/owner/repo/actions/artifacts/1"


def test_main_passes_explicit_apply_and_current_to_prune(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "retain_binaries.py",
            "releases",
            "--repo",
            "owner/repo",
            "--current",
            "v0.3.0",
            "--apply",
        ],
    )
    prune = MagicMock()
    monkeypatch.setattr(retention, "prune", prune)
    retention.main()
    prune.assert_called_once_with("owner/repo", "releases", "v0.3.0", apply=True)


def test_empty_cleanup_is_a_noop(monkeypatch, capsys):
    monkeypatch.setattr(retention, "inventory", lambda *_: [current_release(1)])
    api = MagicMock()
    monkeypatch.setattr(retention, "github_api", api)
    assert retention.prune("owner/repo", "releases", "v0.1.0", apply=True) == []
    api.assert_not_called()
    assert json.loads(capsys.readouterr().out)["delete_ids"] == []


@pytest.mark.parametrize(
    "error,expected",
    [
        (ValueError("Missing current artifact"), "Missing current artifact"),
        (
            subprocess.CalledProcessError(1, ["gh"], stderr="GitHub permission denied"),
            "GitHub permission denied",
        ),
    ],
)
def test_main_reports_clear_failure_without_success(monkeypatch, capsys, error, expected):
    monkeypatch.setattr(
        "sys.argv", ["retention", "artifacts", "--repo", "owner/repo", "--current", "1", "--apply"]
    )
    monkeypatch.setattr(retention, "prune", MagicMock(side_effect=error))
    with pytest.raises(SystemExit) as exit_info:
        retention.main()
    assert exit_info.value.code == 1
    assert expected in capsys.readouterr().err


@pytest.mark.parametrize("asset_index", [0, 1])
def test_incomplete_intermediate_release_does_not_displace_usable_previous(asset_index):
    incomplete = release(2)
    orphan = incomplete["assets"][asset_index]
    incomplete["assets"] = [orphan, incomplete["assets"][2]]
    records = [release(1), incomplete, current_release(3)]
    assert retention.release_deletions(records, "v0.3.0") == [orphan["id"]]


def test_incomplete_releases_are_removed_while_only_complete_pairs_count_toward_limit():
    incomplete = release(3)
    incomplete["assets"] = [incomplete["assets"][1]]
    assert retention.release_deletions(
        [release(1), release(2), incomplete, current_release(4)], "v0.4.0"
    ) == [31, 10, 11]


def test_release_retains_complete_versions_for_each_target():
    first = current_release(1)
    second = current_release(2)
    second["assets"] = second["assets"][:-1]
    records = [first, second, current_release(3)]

    assert retention.release_deletions(records, "v0.3.0") == [10, 11, 23]


def test_current_release_missing_ubuntu_asset_blocks_all_deletions():
    current = current_release(3)
    current["assets"].pop()
    with pytest.raises(ValueError, match="twinkly-cli ubuntu-arm64"):
        retention.release_deletions([release(1), release(2), current], "v0.3.0")


def test_ci_retains_versions_independently_for_each_target():
    say_ubuntu = ("twinkly-cli", "ubuntu-arm64")
    wall_ubuntu = ("twinklywall", "ubuntu-arm64")
    records = [
        artifact(1, "0.1.0"),
        artifact(2, "0.2.0", target=say_ubuntu),
        artifact(3, "0.2.0", target=wall_ubuntu),
        artifact(4, "0.3.0", target=say_ubuntu),
        artifact(5, "0.4.0", target=wall_ubuntu),
        *current_artifacts(6, "0.5.0"),
        artifact(7, "0.6.0", target=("twinklywall", "darwin-arm64")),
        artifact(8, "0.6.0", target=say_ubuntu),
    ]
    runs = success_runs(1, 2, 3, 4, 5)
    runs[8] = {"status": "in_progress", "conclusion": None}
    assert retention.artifact_deletions(records, runs, 6) == [2]


@pytest.mark.parametrize("missing_target", [True, False])
def test_ci_requires_matching_versions_for_all_current_targets(missing_target):
    records = current_artifacts(5, "0.5.0")
    if missing_target:
        records.pop()
    else:
        records[-1]["name"] = "twinkly-cli-0.4.0-ubuntu-arm64"
    with pytest.raises(ValueError, match="all binary artifacts for one version"):
        retention.artifact_deletions(records, {}, 5)


def test_new_release_preserves_legacy_macos_assets():
    legacy = release(1)
    for asset in legacy["assets"][:2]:
        asset["name"] = asset["name"].replace("twinkly-cli", "twinklysay")
    assert retention.release_deletions([legacy, current_release(2)], "v0.2.0") == []
