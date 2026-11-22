---
name: twinkly-cli
description: Use the Twinkly Wall repository's twinkly-cli to list, preview, or play cards, run the wall playlist, configure cards in YAML, or implement and test new Python display cards.
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

## Create or configure a card

Use the [card authoring guide](references/card-authoring.md) for YAML entries, implementing a new card type, registration, and a worked example with a focused test. Preview new types from the updated source checkout. Distributing a new type in a standalone executable requires a rebuild.
