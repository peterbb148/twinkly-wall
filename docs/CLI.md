# Twinkly CLI

`twinkly-cli wall` runs the configured wall playlist. `twinkly-cli say`
provides on-demand cards, text and previews. Update scripts and services to use
the new commands. Existing settings and playlists use the same paths.

## Install with GitHub CLI

From this repository's checkout, authenticate `gh` with an account that can
access the repository. Run the script for your platform:

```bash
bash scripts/install_macos.sh     # Apple Silicon, macOS 15 or newer
bash scripts/install_ubuntu.sh    # Ubuntu 24.04 or 26.04 LTS, ARM64
bash scripts/install_raspberry_pi.sh  # 64-bit Raspberry Pi OS (Trixie)
```

Each script downloads the latest release, checks the published SHA-256, and
installs `twinkly-cli` in `~/.local/bin`. Pass a tag such as `vVERSION` to pin
a release, or set `TWINKLY_INSTALL_DIR` to use a different destination. Add the
destination to your shell's `PATH` and run `twinkly-cli --version` to verify
the installation. Rerun the same installer to upgrade.

The first compatible tag will contain the unified archive. Earlier releases
have their own installation instructions in the tagged source.

## Manual installation on Apple Silicon macOS

The initial binary target is **macOS 15 (Sequoia) or newer, Apple Silicon ARM64**.
Release builds and installation tests run natively on macOS 15.

Download `twinkly-cli-VERSION-darwin-arm64.tar.gz` and its `.sha256` file from
[GitHub Releases](https://github.com/peterbb148/twinkly-wall/releases). Artifacts
appear after a version tag completes the release workflow. Before the first tag,
PR builds are available as a `twinkly-cli-VERSION-darwin-arm64` Actions artifact.

Replace `VERSION` below with the downloaded version:

```bash
shasum -a 256 -c twinkly-cli-VERSION-darwin-arm64.tar.gz.sha256
tar -xzf twinkly-cli-VERSION-darwin-arm64.tar.gz
./twinkly-cli --version
./twinkly-cli --help
mkdir -p "$HOME/.local/bin"
install -m 755 twinkly-cli "$HOME/.local/bin/twinkly-cli"
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
`codesign --verify --strict twinkly-cli` confirms signature integrity, not Apple
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

## Manual installation on Ubuntu ARM64

The Ubuntu builds support **Ubuntu 24.04 LTS and 26.04 LTS on ARM64** (`aarch64`).
Each executable bundles Python and its Python dependencies. It uses the host
glibc and needs writable, executable temporary space to unpack at startup.
Use an Ubuntu 24.04 or 26.04 userspace with the standard runtime libraries.

The Ubuntu archive and its SHA-256 sidecar are available from
[GitHub Releases](https://github.com/peterbb148/twinkly-wall/releases).
Download both files, verify the checksum from the download directory, then
extract and install the executable. Replace `VERSION`
with the release version without the leading `v`.

```bash
version=VERSION
archive="twinkly-cli-$version-ubuntu-arm64.tar.gz"
sha256sum --strict --check "$archive.sha256" &&
  mkdir -p "twinkly-cli-$version" "$HOME/.local/bin" &&
  tar -xzf "$archive" -C "twinkly-cli-$version" &&
  install -m 755 "twinkly-cli-$version/twinkly-cli" "$HOME/.local/bin/twinkly-cli"
```

The archive includes example settings, a playlist, and a sample image.

## Install on Raspberry Pi OS

The Raspberry Pi package targets **64-bit Raspberry Pi OS (Trixie)** with an
ARM64 userspace and a minimum supported runtime of **glibc 2.41**. Debian 13
ARM64 provides the compatible userspace used in CI. You can check your Pi with
`dpkg --print-architecture` (expected `arm64`) and `getconf GNU_LIBC_VERSION`.
The executable bundles Python and its Python dependencies. It needs writable,
executable temporary space to unpack at startup.

Use `bash scripts/install_raspberry_pi.sh` with authenticated `gh`, or download
the matching archive and checksum from [GitHub Releases](https://github.com/peterbb148/twinkly-wall/releases)
once a release includes the Raspberry Pi package. Replace `VERSION` with that
release version without its leading `v`.

```bash
version=VERSION
archive="twinkly-cli-$version-raspberry-pi-arm64.tar.gz"
sha256sum --strict --check "$archive.sha256" &&
  mkdir -p "twinkly-cli-$version" "$HOME/.local/bin" &&
  tar -xzf "$archive" -C "twinkly-cli-$version" &&
  install -m 755 "twinkly-cli-$version/twinkly-cli" "$HOME/.local/bin" &&
  "$HOME/.local/bin/twinkly-cli" --version
```

Keep settings and playlists outside the archive. The archive includes example
YAML files and a sample image. Store optional credentials in the environment
of the account running the daemon.

## Start the wall daemon

Copy the daemon archive's example YAML files to a directory outside the extracted
archive. Set `twinkly.host` to your wall's address and edit the playlist. Try terminal
playback first, then start the daemon on the physical wall with the same files.

```bash
twinkly-cli wall --terminal --settings /path/to/settings.yaml --cards /path/to/cards.yaml
twinkly-cli wall --settings /path/to/settings.yaml --cards /path/to/cards.yaml
```

For an existing systemd service on the Pi, set `ExecStart` to the absolute
path of the installed binary followed by `wall --settings /absolute/settings.yaml
--cards /absolute/cards.yaml`. Give the service account access to those files
and supply optional MCP credentials through its environment. After editing
the unit, reload systemd with `sudo systemctl daemon-reload`, restart the service,
and inspect its log with `journalctl -u twinkly-wall.service`. Use the service's
actual unit name if it differs. Verify a card on the physical LED wall before
accepting a deployment.

## Display orientation and mirroring

Face the front of the wall and find the edge where the LED strands connect to
the controller leads. Set `twinkly.orientation` to that edge. Use `top` or
`bottom` for portrait and `left` or `right` for landscape.

```yaml
twinkly:
  host: 192.168.1.137
  orientation: top
  mirror_h: false
  mirror_v: false
```

Use `mirror_h` to flip left to right and `mirror_v` to flip top to bottom as
viewed on the mounted panel. Either or both can be enabled. The playlist
daemon, single-card playback and terminal preview use the same mapping. Use
`--orientation` with `say preview`, `say card`, or `wall` to override the
saved setting for one invocation. The default is `right`. Existing settings
and commands using `horizontal`, `vertical_left`, or `vertical_right` still
work and correspond to `right`, `top`, and `bottom`, respectively.

To check the mount and mirrors, send the `orientation_test` card. It uses
the saved settings and fits the configured portrait or landscape mount.

```bash
twinkly-cli say card orientation_test --settings config/settings.yaml --duration 10
```

The white arrow should point up. Read the corner markers while facing the
wall. Each corner has a distinct color and dot count.

| | Left | Right |
| --- | --- | --- |
| Top | 1 red dot | 2 green dots |
| Bottom | 3 blue dots | 4 yellow dots |

Confirm the configured wire edge first. If the left and right markers swap,
toggle `mirror_h`. If the top and bottom markers swap, toggle `mirror_v`.

Portrait effects such as `torch_vertical`, `candle_vertical`, and
`beer_vertical` draw on a 10×50 canvas. The torch has a bright base,
uneven flickering tips, and dimming embers. Set `intensity` to adjust flicker
speed or `ember_density` to adjust the number of sparks. Landscape cards such as `clock`
draw on a 50×10 canvas. When a card and the mount have different aspect
orientations, the card turns sideways to fill the panel at native resolution.
Both layouts and crossfades between them use all 500 LEDs.

```bash
twinkly-cli say card torch_vertical --settings config/settings.yaml --duration 12
```

## Commands and compatibility

```bash
twinkly-cli say text "Hello" --color gold
twinkly-cli say list
twinkly-cli say list --playlist /path/to/cards.yaml
twinkly-cli say preview clock --duration 3 --orientation top
twinkly-cli say preview text --text "Hello" --scroll --scroll-direction vertical_up
twinkly-cli say preview --playlist /path/to/cards.yaml --id 1
twinkly-cli say card clock --settings /path/to/settings.yaml --duration 3
twinkly-cli say mcp --server https://your-server.example --interval 2
```

Update scripts and service commands using these mappings:

| Previous command | Twinkly CLI command |
| --- | --- |
| `twinkly-wall [OPTIONS]` | `twinkly-cli wall [OPTIONS]` |
| `twinklysay say "Hello"` | `twinkly-cli say text "Hello"` |
| `twinklysay card clock` | `twinkly-cli say card clock` |
| `twinklysay preview clock` | `twinkly-cli say preview clock` |
| `twinklysay list` | `twinkly-cli say list` |
| `twinklysay mcp` | `twinkly-cli say mcp` |

The existing short options, color formats, card-specific options, playlist IDs,
orientation values, and defaults are retained. Use `twinkly-cli say COMMAND --help`
for the full option list. `--version` uses the package
version. Invoking `twinkly-cli` without arguments shows help successfully.

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

## External cards

Create one YAML file per card in `config/cards.d` when running from the
repository root. The CLI also discovers definitions in
`~/.config/twinkly-wall/cards.d`. Set `TWINKLY_CARD_DIR` to use a single explicit
directory, for example on a portable drive.

The filename without `.yaml` or `.yml` becomes the card name. Names start with
a lowercase letter and can also contain lowercase letters, digits, underscores,
and hyphens. Names must be unique across both directories and the built-in
catalog.

The repository's [party-flame card](../config/cards.d/party-flame.yaml) uses an
external 10×50 GIF. To make your own version, save a definition like this with
its GIF beside it.

```yaml
type: image
layout: portrait
path: flame.gif
scroll: false
```

`type` selects an existing renderer and the remaining keys are its options.
An image path in the definition is relative to the YAML file unless it is
absolute. The portrait image layout is 10×50 and the default landscape layout
is 50×10. Playback duration comes from the command or playlist entry.

```bash
twinkly-cli say list
twinkly-cli say preview party-flame --orientation top --duration 3
twinkly-cli say card party-flame --settings ~/.config/twinkly-wall/portrait.yaml --duration 12
```

The [Skål card](../config/cards.d/skal.yaml) displays the fixed text `SKÅL!`
left to right on the landscape wall. Preview it with your wall's settings so
the terminal uses the same mirror axes:

```bash
twinkly-cli say preview skal --orientation right --settings ./wall-settings.yaml
```

The list includes each external definition's path. For playlist playback, add
an entry with `type: party-flame`. Editing the YAML or replacing the GIF takes
effect when the card is next loaded. Configuration uses the existing renderers
and works with the same installed executable.

## Develop, build, and release

Use UV and Python 3.11 for source installations:

```bash
uv sync --locked
uv run --locked twinkly-cli --help
uv run --locked pytest --cov=twinkly_wall.cli --cov=scripts.retain_binaries --cov=twinkly_wall.command --cov-branch --cov-report=term-missing --cov-fail-under=81
uv run --locked coverage report --include='scripts/retain_binaries.py' --fail-under=81
uv run --locked ruff check src/ tests/ scripts/ packaging/
uv run --locked ruff format --check src/ tests/ scripts/ packaging/
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
`packaging/twinkly-cli.spec`, checks ARM64 architecture and the ad-hoc signature,
runs smoke tests with an empty executable search path outside the checkout, then
creates the archive and checksum in `dist/`. A local build is validated only on
its host OS; use the macOS 15 CI artifact for the documented release target.

On PRs and pushes to `main`, CI always runs tests, lint, formatting, and
dependency auditing. It builds and smoke-tests the platform archives only when
one of these CLI source files changes:

- `src/twinkly_wall/command.py` (entry point and command dispatcher)
- `src/twinkly_wall/cli.py` (the `say` commands)
- `src/twinkly_wall/daemon.py` (the `wall` command)

Changes to cards (including registration), docs, YAML configs, assets, and
other files outside this list skip binary builds, install jobs, and artifact
cleanup. A manual CI dispatch or a version-tag release builds every platform.

Mac CI tests the downloaded archive on a second macOS 15 runner. Only the test
harness uses the runner's Python. The executable receives no Python or UV on
`PATH`.

To build the Ubuntu archive locally, run `bash scripts/build_ubuntu.sh` on
native Ubuntu 24.04 ARM64 with UV, Python 3.11, and binutils installed. Each
Ubuntu CI install job downloads the archive and verifies its checksum,
executable architecture, CLI rendering, and daemon terminal playback and
shutdown in a clean Ubuntu ARM64 container without Python or UV installed.

To build the Raspberry Pi archive locally, run `bash scripts/build_raspberry_pi.sh`
on a 64-bit Trixie system with UV, system Python 3.13, its shared library
(`libpython3.13`), and binutils installed. CI builds on an ARM64 runner in a
Debian Trixie userspace, then downloads the archive into a clean Trixie
userspace without Python or UV. The smoke test checks the checksum, the ARM64
executable, both CLI modes, and the installer.

For a release, update both `pyproject.toml` and `twinkly_wall.__version__`, update
the lockfile, and deliver the changes through a reviewed PR. Once merged, create
the corresponding `vVERSION` tag. `.github/workflows/release.yml` checks that the
tag matches both versions, runs the same tests and native build/install jobs,
and publishes the verified archive and checksum for each command and platform
to GitHub Releases. A failed build or test prevents publication. Creating a workflow does not itself publish a release.

## Binary retention

Only the **current and previous binary versions** are retained for each distribution:

- GitHub Releases keep archives and checksums for the two most recently published
  complete binary versions (each with its archive and checksum). Incomplete
  releases do not displace the previous usable version. After a successful
  publication, older or incomplete binary assets are deleted;
  their Git tags, release notes, source archives, and unrelated assets remain.
- Actions keep the newest verified build of each of the two latest binary versions,
  ordered by artifact creation time. Superseded builds of the same version,
  completed failed builds, and legacy unversioned binary artifacts are removed
  after a new build passes the full test/build/install checks. Other active runs
  are left alone until they finish.

Cleanup is serialized with GitHub's `queue: max` so queued publications are not
replaced by incoming cleanup jobs, and reads back the inventory to verify deletions. A bounded retry allows for
records that GitHub still lists briefly after deletion. A failed
build, failed publication, or missing current archive/artifact prevents cleanup.
API errors fail the job visibly. Actions' ordinary artifact expiry still applies;
GitHub Releases provide the persistent downloads for the two retained versions.
