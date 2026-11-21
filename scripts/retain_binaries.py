"""Retain only the two newest Twinklysay binary versions through the GitHub CLI."""

import argparse
import json
import re
import subprocess
from typing import Any

ARTIFACT_NAME = re.compile(r"twinklysay-(.+)-darwin-arm64\Z")
LEGACY_ARTIFACT = "twinklysay-darwin-arm64"


def release_deletions(releases: list[dict], current_tag: str) -> list[int]:
    """Plan removal of older archive/checksum assets, preserving release metadata."""
    versions = []
    for release in releases:
        if release["draft"]:
            continue
        version = release["tag_name"].removeprefix("v")
        archive = f"twinklysay-{version}-darwin-arm64.tar.gz"
        assets = [a for a in release["assets"] if a["name"] in {archive, archive + ".sha256"}]
        if assets:
            versions.append((release, assets))
    current_assets = [a for r, assets in versions if r["tag_name"] == current_tag for a in assets]
    if len(current_assets) != 2:
        raise ValueError("Current release must contain both its binary archive and checksum")
    versions.sort(key=lambda item: item[0]["published_at"], reverse=True)
    complete = [(release, assets) for release, assets in versions if len(assets) == 2]
    keep = {asset["id"] for _, assets in complete[:2] for asset in assets}
    return [asset["id"] for _, assets in versions for asset in assets if asset["id"] not in keep]


def artifact_deletions(artifacts: list[dict], runs: dict[int, dict], current_run: int) -> list[int]:
    """Keep the newest build of each of the two latest verified binary versions.

    Other active runs are untouched. Completed failed builds and superseded duplicate
    builds can be removed once this run has passed its installation tests.
    """
    candidates = [
        a
        for a in artifacts
        if not a["expired"] and (ARTIFACT_NAME.fullmatch(a["name"]) or a["name"] == LEGACY_ARTIFACT)
    ]
    if not any(
        a["workflow_run"]["id"] == current_run and ARTIFACT_NAME.fullmatch(a["name"])
        for a in candidates
    ):
        raise ValueError("Current verified run has no versioned binary artifact")
    eligible = [
        a
        for a in candidates
        if a["workflow_run"]["id"] == current_run
        or runs[a["workflow_run"]["id"]]["status"] == "completed"
    ]
    verified = [
        a
        for a in eligible
        if ARTIFACT_NAME.fullmatch(a["name"])
        and (
            a["workflow_run"]["id"] == current_run
            or runs[a["workflow_run"]["id"]]["conclusion"] == "success"
        )
    ]
    keep, versions = set(), set()
    for artifact in sorted(verified, key=lambda a: a["created_at"], reverse=True):
        version = ARTIFACT_NAME.fullmatch(artifact["name"])[1]
        if version not in versions and len(versions) < 2:
            versions.add(version)
            keep.add(artifact["id"])
    return [a["id"] for a in eligible if a["id"] not in keep]


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
            if not a["expired"]
            and (ARTIFACT_NAME.fullmatch(a["name"]) or a["name"] == LEGACY_ARTIFACT)
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
