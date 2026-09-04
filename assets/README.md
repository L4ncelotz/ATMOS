# assets/

This directory holds media for the project's README.

- `demo.svg` — a static four-scene preview. Used by
  `README.md` until a real terminal recording lands.
- `demo.gif` — when a real asciinema or ttyrec-to-gif capture
  becomes available, drop it at this path. The README
  references `assets/demo.gif`; replace the `<img src="demo.svg">`
  with `![ATMOS Demo](demo.gif)` (and remove `demo.svg`).

ATMOS is a terminal-native application: there is no GUI to
screenshot. The SVG is the closest static approximation, with
one panel per major scene type.
