"""Retain the two newest binary versions per command and platform."""

import argparse
import json
import re
import subprocess
from collections import defaultdict
from typing import Any

CURRENT_TARGETS = (
    ("twinkly-cli", "darwin-arm64"),
    ("twinkly-cli", "ubuntu-arm64"),
)
BINARY_TARGETS = CURRENT_TARGETS + (
    ("twinklysay", "darwin-arm64"),
    ("twinklysay", "ubuntu-arm64"),
    ("twinklywall", "ubuntu-arm64"),
)
ARTIFACT_NAME = re.compile(
    r"(twinkly-cli|twinklysay|twinklywall)-(.+)-(darwin-arm64|ubuntu-arm64)\Z"
)
LEGACY_ARTIFACT = "twinklysay-darwin-arm64"


def artifact_identity(name: str) -> tuple[tuple[str, str], str] | None:
    """Extract the command, platform, and version of a supported artifact."""
    match = ARTIFACT_NAME.fullmatch(name)
    if match:
        command, version, platform = match.groups()
        if (command, platform) in BINARY_TARGETS:
            return (command, platform), version
    return None


def release_deletions(releases: list[dict], current_tag: str) -> list[int]:
    """Plan removal of old asset pairs, preserving release metadata."""
    published = sorted(
        (release for release in releases if not release["draft"]),
        key=lambda release: release["published_at"],
        reverse=True,
    )
    deletions = []
    for command, platform in BINARY_TARGETS:
        complete_versions = 0
        current_complete = False
        for release in published:
            version = release["tag_name"].removeprefix("v")
            archive = f"{command}-{version}-{platform}.tar.gz"
            assets = {
                asset["name"]: asset["id"]
                for asset in release["assets"]
                if asset["name"] in {archive, archive + ".sha256"}
            }
            if len(assets) == 2:
                current_complete |= release["tag_name"] == current_tag
                complete_versions += 1
                if complete_versions <= 2:
                    continue
            deletions.extend(assets.values())
        if (command, platform) in CURRENT_TARGETS and not current_complete:
            raise ValueError(
                f"Current release must contain the archive and checksum for {command} {platform}"
            )
    return deletions


def artifact_deletions(artifacts: list[dict], runs: dict[int, dict], current_run: int) -> list[int]:
    """Keep the two latest verified versions per target and protect active runs."""
    candidates = []
    current_targets = defaultdict(set)
    for artifact in artifacts:
        identity = artifact_identity(artifact["name"])
        if artifact["expired"] or (identity is None and artifact["name"] != LEGACY_ARTIFACT):
            continue
        candidates.append((artifact, identity))
        if (
            artifact["workflow_run"]["id"] == current_run
            and identity is not None
            and identity[0] in CURRENT_TARGETS
        ):
            target, version = identity
            current_targets[version].add(target)
    if len(current_targets) != 1 or next(iter(current_targets.values())) != set(CURRENT_TARGETS):
        raise ValueError("Current verified run must have all binary artifacts for one version")

    eligible = []
    for artifact, identity in candidates:
        run_id = artifact["workflow_run"]["id"]
        if run_id == current_run:
            eligible.append((artifact, identity, True))
        elif runs[run_id]["status"] == "completed":
            eligible.append((artifact, identity, runs[run_id]["conclusion"] == "success"))

    keep = set()
    versions_by_target = defaultdict(set)
    for artifact, identity, verified in sorted(
        eligible, key=lambda entry: entry[0]["created_at"], reverse=True
    ):
        if identity is None or not verified:
            continue
        target, version = identity
        versions = versions_by_target[target]
        if version not in versions and len(versions) < 2:
            versions.add(version)
            keep.add(artifact["id"])
    return [artifact["id"] for artifact, _, _ in eligible if artifact["id"] not in keep]


def github_api(endpoint: str, *, paginate: bool = False, delete: bool = False) -> Any:
    """Call GitHub, propagating API and authentication failures without retries."""
    command = ["gh", "api", endpoint]
    if paginate:
        command += ["--paginate", "--slurp"]
    if delete:
        command += ["--method", "DELETE"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return None if delete else json.loads(result.stdout)


def inventory(repo: str, kind: str) -> list[dict]:
    """Read every page of release or artifact records."""
    endpoint = "releases" if kind == "releases" else "actions/artifacts"
    pages = github_api(f"repos/{repo}/{endpoint}?per_page=100", paginate=True)
    return [item for page in pages for item in (page if kind == "releases" else page["artifacts"])]


def prune(repo: str, kind: str, current: str, *, apply: bool = False) -> list[int]:
    """Plan deletions, optionally apply them, then verify the removed IDs are absent."""
    records = inventory(repo, kind)
    if kind == "releases":
        ids = release_deletions(records, current)
        endpoint = "releases/assets"
    else:
        relevant = [
            a
            for a in records
            if not a["expired"] and (artifact_identity(a["name"]) or a["name"] == LEGACY_ARTIFACT)
        ]
        run_ids = {a["workflow_run"]["id"] for a in relevant}
        runs = {run_id: github_api(f"repos/{repo}/actions/runs/{run_id}") for run_id in run_ids}
        ids = artifact_deletions(records, runs, int(current))
        endpoint = "actions/artifacts"
    print(json.dumps({"kind": kind, "delete_ids": ids, "apply": apply}))
    if apply and ids:
        for item_id in ids:
            github_api(f"repos/{repo}/{endpoint}/{item_id}", delete=True)
        remaining = inventory(repo, kind)
        remaining_ids = (
            {a["id"] for r in remaining for a in r["assets"]}
            if kind == "releases"
            else {a["id"] for a in remaining}
        )
        if remaining_ids.intersection(ids):
            raise RuntimeError("Binary retention deletion could not be verified")
    return ids


def main() -> None:
    """Run retention after a verified CI build or successful release publication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["releases", "artifacts"])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--current", required=True, help="Published tag or verified CI run ID")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        prune(args.repo, args.kind, args.current, apply=args.apply)
    except subprocess.CalledProcessError as error:
        parser.exit(error.returncode, error.stderr or str(error))
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
