# Author a Twinkly Wall card

## Configure an existing type

Check [the example playlist](../../../../config/cards.example.yaml) and the card's implementation for supported options. Add an entry under `cards` in your playlist. The loader passes keys such as `color` and `format_24h` to the card and handles playlist settings such as duration and transition.

```yaml
cards:
  - type: clock
    duration: 3
    color: [255, 215, 0]
    format_24h: true
```

Use `twinkly-cli say list --playlist ./cards.yaml` to get the entry ID and `twinkly-cli say preview --playlist ./cards.yaml --id 1` to preview that entry with its settings from the playlist.

## Implement a new type

Follow the [card contract and registry](../../../../src/twinkly_wall/cards/base.py). Subclass `Card`, choose a unique `card_type`, apply `@register_card`, and import the class in [the cards package](../../../../src/twinkly_wall/cards/__init__.py) so the decorator runs when the CLI loads the package. Follow the package's `__all__` convention for the new class.

`frames(ctx)` yields `(frame, delay)` pairs. The delay is in seconds, and
`frame[y][x]` is an RGB tuple. Choose the canvas for the card's intended layout.

| Layout | Width × height | Canvas |
| --- | --- | --- |
| Landscape | 50 × 10 | `Canvas()` or `Canvas(WIDTH, HEIGHT)` |
| Portrait | 10 × 50 | `Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)` |

Import the dimension constants from `..types`. Draw with the origin at the
upper-left of the card's logical canvas. Terminal previews and hardware output
apply the [mount and mirror settings](../../../../docs/CLI.md#display-orientation-and-mirroring).
When the card layout differs from the mount, the output turns it sideways to
fill the display. `mirror_h` flips viewer-left to viewer-right and `mirror_v`
flips top to bottom.

For a portrait card, use the portrait dimensions both to create the canvas
and to position elements. For example, draw a marker at the bottom-left of
the portrait canvas.

```python
from ..canvas import Canvas
from ..types import GOLD, PORTRAIT_HEIGHT, PORTRAIT_WIDTH

canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
canvas.fill_rect(0, PORTRAIT_HEIGHT - 3, 5, 3, GOLD)
```

A portrait frame test should check for 50 rows of 10 pixels and verify that
the marker reaches the bottom rows. Use `say preview --orientation vertical_left`
or `vertical_right` to preview a portrait mount.

## Worked example

Create `src/twinkly_wall/cards/corner_beacon.py`. This static card lights a gold rectangle in the upper-left corner for the configured duration.

```python
from collections.abc import Iterator

from ..canvas import Canvas
from ..types import GOLD, Frame
from .base import Card, CardContext, register_card


@register_card
class CornerBeaconCard(Card):
    """Show a gold marker in the frame's upper-left corner."""

    card_type = "corner_beacon"

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Yield the marker and its display duration."""
        canvas = Canvas()
        canvas.fill_rect(0, 0, 5, 3, GOLD)
        yield canvas.copy(), self.duration
```

Import `CornerBeaconCard` with `from .corner_beacon import CornerBeaconCard` in `cards/__init__.py` and add `"CornerBeaconCard"` to `__all__`.

Save a separate `corner-beacon.yaml` at the repository root for the example preview.

```yaml
cards:
  - type: corner_beacon
    duration: 0.2
```

Add a focused test in `tests/test_cards_corner_beacon.py`. Resolve the card through the public registry so the test exercises package registration. See [the clock card tests](../../../../tests/test_cards_clock.py) for additional patterns.

```python
from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.types import BLACK, GOLD


def test_corner_beacon_renders_registered_card() -> None:
    card = create_card("corner_beacon", {"duration": 0.2})
    assert card is not None

    [(frame, delay)] = list(card.frames(CardContext()))
    assert len(frame) == 10
    assert all(len(row) == 50 for row in frame)
    assert frame[0][:6] == [GOLD] * 5 + [BLACK]
    assert frame[2][4] == GOLD
    assert frame[3][0] == BLACK
    assert delay == 0.2
```

From the source checkout, run the test, confirm card discovery, and render a short terminal preview. Use the playlist entry to exercise its configuration.

```bash
uv run --locked pytest tests/test_cards_corner_beacon.py
uv run --locked twinkly-cli say list --playlist ./corner-beacon.yaml
uv run --locked twinkly-cli say preview --playlist ./corner-beacon.yaml --id 1 --no-color
```

The installed binary contains the card code from its build. Follow the [release workflow](../../../../docs/CLI.md#develop-build-and-release) when distributing a build with the new card.
