# Twinklysay CLI

`twinklysay` uses Typer and supports `say`, `preview`, `card`, `list`, and `mcp`.
The separate `twinkly-wall` daemon remains available for source-based Raspberry Pi
installations; it is not part of the initial executable release.

## Install on Apple Silicon macOS

The initial binary target is **macOS 14 (Sonoma) or newer, Apple Silicon ARM64**.
Release builds and installation tests run natively on macOS 14. Intel macOS,
Rosetta, Linux, and Windows binaries are not supplied.

Download `twinklysay-VERSION-darwin-arm64.tar.gz` and its `.sha256` file from
[GitHub Releases](https://github.com/peterbb148/twinkly-wall/releases). Artifacts
appear after a version tag completes the release workflow. Before the first tag,
PR builds are available as a `twinklysay-VERSION-darwin-arm64` Actions artifact.

Replace `VERSION` below with the downloaded version:

```bash
shasum -a 256 -c twinklysay-VERSION-darwin-arm64.tar.gz.sha256
tar -xzf twinklysay-VERSION-darwin-arm64.tar.gz
./twinklysay --version
./twinklysay --help
mkdir -p "$HOME/.local/bin"
install -m 755 twinklysay "$HOME/.local/bin/twinklysay"
```

Add `$HOME/.local/bin` to your shell's `PATH` if necessary. The executable bundles
Python, Typer, Pillow, YAML support, certificate data, and the built-in bitmap
fonts. It requires neither Python nor UV to run. The archive also contains example
configuration files, a sample image, and the optional `checks/smoke_binary.py`
verification harness. Your own settings, playlists, and images remain external.

To upgrade, verify the new archive and replace the executable using the same
`install` command. Keep configuration in your user directory so upgrades do not
overwrite it.

### Signing and first launch

Initial executables have PyInstaller's **ad-hoc code signature**. They are not
signed with an Apple Developer identity and are not notarized. A successful
`codesign --verify --strict twinklysay` confirms signature integrity, not Apple
notarization or publisher identity. A SHA-256 checksum detects corruption; it is
not a publisher signature.

macOS may block a browser-downloaded executable on first launch. After checking
the release source and checksum, use **System Settings → Privacy & Security →
Open Anyway** for the blocked executable, then retry. Do not disable Gatekeeper
globally. CI smoke tests do not simulate browser quarantine or prove Gatekeeper
acceptance.

Future Developer ID signing/notarization requires an Apple Developer membership,
a Developer ID Application certificate and its private key/password in CI secrets,
and notarization credentials (an App Store Connect API key or suitable Apple ID
credentials). These credentials are not configured by this change.

## Commands and compatibility

```bash
twinklysay say "Hello" --color gold
twinklysay list
twinklysay list --playlist /path/to/cards.yaml
twinklysay preview clock --duration 3 --orientation vertical_left
twinklysay preview text --text "Hello" --scroll --scroll-direction vertical_up
twinklysay preview --playlist /path/to/cards.yaml --id 1
twinklysay card clock --settings /path/to/settings.yaml --duration 3
twinklysay mcp --server https://your-server.example --interval 2
```

The existing command names, short options, color formats, card-specific options,
playlist IDs, orientation values, and default values are retained. Use
`twinklysay COMMAND --help` for the full option list. `--version` uses the package
version. Invoking `twinklysay` without arguments shows help successfully.

Typer replaces argparse help/error formatting and validates option types. Explicit
configuration/playlist paths must exist and contain valid YAML mappings; playlist
entries must name registered cards. Durations, speeds, polling intervals, and
playlist IDs must be positive; snow wind is between -1 and 1. Invalid arguments
exit with code 2. Rendering/configuration/device errors exit with code 1.
Interruptions restore terminal state; a single preview interruption exits 130,
while an intentional stop of a looping playlist or MCP client exits successfully.

`preview` also accepts `--settings`/`-s` so explicit settings control both the
preview orientation and its data sources. `card --settings` now uses those same
settings for data sources as well as the output device. Device output requires
`twinkly.host`; an unavailable MCP server during initial registration fails the
command instead of entering an apparently successful polling loop.

The CLI does not provision or discover devices. Physical LED output needs a
reachable Twinkly device; terminal previews work without it. Network-dependent
cards need their configured providers.

## Configuration and external files

Settings and playlist discovery retain this order:

1. `config/settings.yaml` / `config/cards.yaml` in the current working directory.
2. `settings.yaml` / `cards.yaml` in the current working directory.
3. `~/.config/twinkly-wall/settings.yaml` / `~/.config/twinkly-wall/cards.yaml`.

If no file is found, existing built-in defaults apply. An explicitly provided
path takes precedence. No local repository settings or credentials are embedded
in the executable. Start from the archive's `examples/` files; use explicit paths
for portable usage. Image paths retain the existing resolution relative to the
working directory (`config/`, then `assets/`, then the given path). Absolute image
paths avoid working-directory dependencies.

The MCP client still supports `TWINKLY_MCP_URL` and `TWINKLY_API_KEY`;
`--server` and `--api-key` take precedence over the corresponding environment
variables. The API key is not printed in CLI startup output.

## Develop, build, and release

Use UV and Python 3.11 for source installations:

```bash
uv sync --locked
uv run --locked twinklysay --help
uv run --locked pytest --cov=twinkly_wall.cli --cov=scripts.retain_binaries --cov-branch --cov-report=term-missing --cov-fail-under=81
uv run --locked coverage report --include='scripts/retain_binaries.py' --fail-under=81
uv run --locked ruff check src/ tests/ scripts/ packaging/entrypoint.py
uv run --locked ruff format --check src/ tests/ scripts/ packaging/entrypoint.py
```

The full test suite runs; CI measures coverage for the CLI being migrated,
including its rendering handlers, and the binary retention script. Each must
exceed 80% coverage. MCP registration/polling and
device output tests use mocks. They do not certify a live server or LED hardware.

On native Apple Silicon macOS, run:

```bash
bash scripts/build_macos.sh
```

This installs the locked build group, builds a single executable using
`packaging/twinklysay.spec`, checks ARM64 architecture and the ad-hoc signature,
runs smoke tests with an empty executable search path outside the checkout, then
creates the archive and checksum in `dist/`. A local build is validated only on
its host OS; use the macOS 14 CI artifact for the documented release target.

PR CI builds the executable and tests the downloaded archive on a second macOS 14
runner with no source checkout or build environment. Only the test harness uses
the runner's Python; the executable receives no Python/UV on `PATH`.

For a release, update both `pyproject.toml` and `twinkly_wall.__version__`, update
the lockfile, and deliver the changes through a reviewed PR. Once merged, create
the corresponding `vVERSION` tag. `.github/workflows/release.yml` checks that the
tag matches both versions, runs the same tests and native build/install jobs,
and publishes the verified archive/checksum to GitHub Releases. A failed build or
test prevents publication. Creating a workflow does not itself publish a release.

## Binary retention

Only the **current and previous binary versions** are retained for each distribution:

- GitHub Releases keep archives and checksums for the two most recently published
  binary versions. After a successful publication, older binary assets are deleted;
  their Git tags, release notes, source archives, and unrelated assets remain.
- Actions keep the newest verified build of each of the two latest binary versions,
  ordered by artifact creation time. Superseded builds of the same version,
  completed failed builds, and legacy unversioned binary artifacts are removed
  after a new build passes the full test/build/install checks. Other active runs
  are left alone until they finish.

Cleanup is serialized and reads back the inventory to verify deletions. A failed
build, failed publication, or missing current archive/artifact prevents cleanup.
API errors fail the job visibly. Actions' ordinary artifact expiry still applies;
GitHub Releases provide the persistent downloads for the two retained versions.
