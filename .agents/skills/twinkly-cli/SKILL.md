---
name: twinkly-cli
description: Use the Twinkly Wall repository's twinkly-cli to list, preview, or play cards, run the wall playlist, check orientation and mirroring, configure cards in YAML, or implement and test new Python display cards.
---

# Twinkly CLI

Use `twinkly-cli say` for on-demand actions and `twinkly-cli wall` for continuous playlist playback. Run `twinkly-cli --version` to identify the installed executable. From the repository, use `uv run --locked twinkly-cli` to exercise source changes. Use the [CLI reference](../../../docs/CLI.md) for installation, configuration discovery, and command options.

## Use existing cards

```bash
twinkly-cli say list
twinkly-cli say text "Hello" --color gold
twinkly-cli say preview clock --duration 3 --no-color
twinkly-cli say list --playlist ./cards.yaml
twinkly-cli say preview --playlist ./cards.yaml --id 1 --settings ./settings.yaml
twinkly-cli wall --terminal --settings ./settings.yaml --cards ./cards.yaml
```

In these examples, `settings.yaml` and `cards.yaml` are the chosen files. Playlist IDs are one-based. The last command loops until stopped. Use a terminal preview to check rendering and orientation.

For physical output, use settings with the intended wall's `twinkly.host`. `twinkly-cli say card clock --settings ./settings.yaml --duration 3` sends one card directly to that wall. `twinkly-cli wall --settings ./settings.yaml --cards ./cards.yaml` runs the playlist on the wall until stopped. Use physical output when requested.

## Check wall orientation and mirroring

Run these commands from the repository root with the intended wall's settings.

```bash
uv run --locked twinkly-cli say preview orientation_test --settings config/settings.yaml --duration 3
uv run --locked twinkly-cli say card orientation_test --settings config/settings.yaml --duration 10
```

Use `say card` when the user requests a physical test. Start with the saved
settings. To try a different mount for one run, pass `--orientation <side>`
to either command. The side can be `top`, `bottom`, `left`, or `right`.

Face the wall. Set `twinkly.orientation` to the edge where the wires connect.
The white arrow should point up, with one red dot at top left, two green dots
at top right, three blue dots at bottom left, and four yellow dots at bottom
right. After confirming the wire edge, toggle `mirror_h` if left and right are
swapped or `mirror_v` if top and bottom are swapped. See the
[orientation and mirroring guide](../../../docs/CLI.md#display-orientation-and-mirroring).

## Create or configure a card

For a named YAML card backed by a built-in renderer, put its definition and assets
in `config/cards.d` at the repository root or `~/.config/twinkly-wall/cards.d`.
Use [external cards](../../../docs/CLI.md#external-cards) for the definition format.

Use the [card authoring guide](references/card-authoring.md) for YAML entries, implementing a new card type, registration, and a worked example with a focused test. Preview new types from the updated source checkout. Bundling a new Python renderer in a standalone executable requires a rebuild.
