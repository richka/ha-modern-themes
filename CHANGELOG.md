# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Removed ten theme variables that nothing reads, all of them legacy names with no
  declaration and no reader in the frontend or in any installed card:
  `accent-text-color`, `body-font-size`, `card-title-font-size`,
  `card-title-font-weight`, `dark-theme-disabled-color`,
  `light-theme-disabled-color`, `ha-card-header-font-weight`,
  `ha-card-header-letter-spacing`, `hue-primary-color` and
  `sidebar-selected-background-color`.
- `tools/build.py` now asserts what the README promises: the full
  `ha-color-primary-05 … -95` ramp, both color modes, and an identical key set in
  every variant. It also generates the variant table in `README.md`, so the table
  cannot drift from the file.
- `tools/check_vars.py` ignores `setProperty()` writes, gained `--ref` (check
  against a pinned frontend tag) and `--strict-baseline` (fail when a baseline
  entry stops being unread).
- CI runs the variable check against the frontend tag that matches the installed
  Home Assistant, not against a moving branch tip.

## [1.0.0] - 2026-11-18

### Added

- Eleven theme variants: Red (base), Blue, Green, Orange, Purple, Slate, Teal, Amber,
  Indigo, Pink, Graphite.
- Light and dark modes for every variant, with backgrounds tinted to match the brand
  color instead of a single shared surface palette.
- Full `--ha-color-primary-05 … --ha-color-primary-95` ramp generated per variant.
- Legacy `paper-*`, `mdc-*` and Material tokens so older cards match the modern look.
- State colors: generic active/inactive, plus climate, water heater, alarm control
  panel, lock, battery, media player, person, plant, siren, update, sun, vacuum, valve,
  fan, cover and lawn mower.
- Climate heating follows the brand color; cooling, auto, dry and fan-only stay
  semantic.
- Water heater modes (`eco`, `electric`, `gas`, `heat_pump`, `high_demand`,
  `performance`) follow the brand color instead of the default orange shades.
- Dashboard edit-mode top bar themed per variant (Home Assistant otherwise hard-codes
  `#455a64`).
- Typography based on Segoe UI Variable, plus `--ha-font-*`, `paper-font-*` and
  `mdc-typography-*` aliases.
- Geometry, elevation and form tokens.
- `--font-stack` compatibility alias so CSS written for older themes keeps working.

### Notes

- No card-mod and no shadow-DOM patches: variables only, for upgrade safety.
- Requires Home Assistant 2025.8 or newer, the first release with the `--ha-color-*`
  token set. Older releases load the theme but keep their default colors on the newest
  components.
- `themes/modern.yaml` is generated from `src/modern.src.yaml` by `tools/build.py`. The
  shipped file contains no YAML anchors or merge keys, so installing it does not produce
  `duplicate key` warnings in the Home Assistant log.
- Theme comments are in English.
