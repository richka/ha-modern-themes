# Modern Themes for Home Assistant

A modern, native theme family for **Home Assistant 2026.x** — eleven color variants,
each with a light and a dark mode, built entirely from Home Assistant's own theme
variables.

No `card-mod`. No shadow-DOM CSS patches. No custom frontend code. Just theme tokens,
so the themes keep working across Home Assistant updates.

> **Inspired by** [Metrology for Hass](https://github.com/Madelena/Metrology-for-Hass)
> by Madelena Mak, and by Microsoft's Fluent and Metro design languages.
> Modern Themes is an independent implementation written from scratch against Home
> Assistant 2026 theme variables. It does not contain or redistribute Metrology's code.

---

## Variants

| Theme | Primary | Accent | Text on primary |
| --- | --- | --- | --- |
| **Modern Red** (base) | `#C30052` | `#E90062` | white |
| **Modern Blue** | `#0078D7` | `#008DFD` | white |
| **Modern Green** | `#00CB6A` | `#00F17D` | black |
| **Modern Orange** | `#FF8C00` | `#FF9D00` | black |
| **Modern Purple** | `#6A00CB` | `#A94DFF` | white |
| **Modern Slate** | `#4F5A68` | `#677385` | white |
| **Modern Teal** | `#008272` | `#00B294` | white |
| **Modern Amber** | `#C77D00` | `#FFB900` | black |
| **Modern Indigo** | `#4B53BC` | `#6B73E8` | white |
| **Modern Pink** | `#C239B3` | `#E3008C` | white |
| **Modern Graphite** | `#5D5D5D` | `#8A8A8A` | white |

All variants share one design language; only the brand color, the generated
`--ha-color-primary-*` ramp and the tinted background surfaces change.

## What it styles

- **Brand ramp** — the full `--ha-color-primary-05 … --ha-color-primary-95` scale,
  derived from each variant's primary color.
- **Legacy tokens** — `paper-*`, `mdc-*` and Material variables, so older cards and
  dialogs match the modern look.
- **Surfaces** — primary/secondary/card backgrounds, dividers, outlines, dialogs,
  sidebar, top app bar, and the dashboard **edit-mode** app bar.
- **State colors** — active/inactive defaults plus domain-specific mapping for
  climate (`heat`, `cool`, `heat_cool`, `auto`, `dry`, `fan_only`, `off`),
  water heater (`eco`, `electric`, `gas`, `heat_pump`, `high_demand`, `performance`),
  alarm control panel, lock, battery, media player, person, plant, siren, update,
  sun, vacuum, valve, fan, cover, lawn mower and more.
- **Typography** — `--ha-font-family-*` set to Segoe UI Variable with system fallbacks,
  plus `paper-font-*` and `mdc-typography-*` aliases.
- **Geometry and elevation** — `--ha-border-radius-*`, `--ha-box-shadow-*`,
  `--ha-picture-border-radius`, `--wa-panel-border-radius`.
- **Forms** — input fill, ink, outline and hover colors in both modes.
- **HACS** badges and status colors.
- **Light and dark** — every variant ships both, via `modes:`.

## Requirements

- Home Assistant **2026.11** or newer (the themes use `--ha-color-*`, `--wa-*` and the
  current state-color resolution order).
- No integrations, no HACS plugins, no card-mod.

Older Home Assistant versions will ignore unknown tokens: the themes will still apply,
but newer surfaces may keep their default colors.

## Installation

### Marketplace (Home Assistant 2026.11+)

1. **Settings → Marketplace**
2. Open the menu and choose **Add from link** (custom repository)
3. Paste `https://github.com/richka/ha-modern-themes`
4. Install, then reload the page

### HACS

1. HACS → **Frontend**
2. Three-dot menu → **Custom repositories**
3. URL: `https://github.com/richka/ha-modern-themes`, category: **Theme**
4. Install, then reload the page

### Manual

Copy `themes/modern.yaml` to your configuration directory:

```
/config/themes/modern.yaml
```

Make sure themes are included in `configuration.yaml`:

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

Then reload:

- **Developer tools → Actions → `frontend.reload_themes`**, or
- restart Home Assistant.

Finally, hard-refresh the browser (`Ctrl + F5`) so the new CSS variables are picked up.

> ⚠️ Install the file **once**. Theme names are global: a second copy (for example one
> from HACS plus a hand-copied file) creates duplicate names, and which one wins depends
> on file order.

## Choosing a theme

**Per user** — **Profile → Theme** (this is the normal way; every user picks their own).

**Per view** — add `theme` to a view in the dashboard editor:

```yaml
views:
  - title: Home
    path: home
    theme: Modern Red
```

**Server default** — for users who have not picked a theme in their profile:

```yaml
action: frontend.set_theme
data:
  name: Modern Red
  mode: light
```

Repeat with `mode: dark` for the dark-mode default. The selection is stored in
`.storage/frontend.theme`. To go back to the built-in theme:

```yaml
action: frontend.set_theme
data:
  name: default
```

## How it is built

The repository keeps the themes DRY and the published file boring:

| Path | What it is |
| --- | --- |
| `src/modern.src.yaml` | the source: `Modern Red: &modern_base` holds every token once, `&modern_light` / `&modern_dark` hold the mode surfaces, and the other ten variants merge the base (`<<: *modern_base`) and override only the brand color, the primary ramp, the on-primary text color and the tinted backgrounds |
| `themes/modern.yaml` | the file Home Assistant loads: the same eleven themes with every merge expanded, generated by `tools/build.py` |
| `tools/build.py` | expands the source and verifies the result parses to exactly the same data |

Why the expansion exists: Home Assistant's YAML loader reports every key that overrides a
merged anchor as a `duplicate key` warning. The themes themselves work either way, but a
published theme should not fill the log with warnings — so the shipped file has no
anchors and no merge keys at all.

Editing:

```bash
# after changing src/modern.src.yaml
python tools/build.py          # rewrite themes/modern.yaml
python tools/build.py --check  # verify the checked-in file is current
```

Requires Python 3.11+ and PyYAML (`pip install pyyaml`).

One fix in the source therefore applies to all eleven variants, and the generated file
stays a flat, greppable list of complete themes for people who prefer to read or patch it
directly.

## Known limitations

- **No card-mod layer.** This is deliberate: Metrology's look comes largely from
  card-mod CSS that breaks on Home Assistant upgrades. If you want those layout tweaks
  (uppercase headers, tighter row spacing, glass dialogs), install card-mod and add
  them yourself.
- **Custom cards and floorplans** follow the theme only if their CSS uses the theme
  variables (for example `fill: var(--primary-color)` inside an SVG). Hard-coded colors
  stay hard-coded.
- **Entity colors win.** A light whose entity reports `rgb_color` will show its real
  color on buttons; state colors are a fallback, not an override.
- **Theme names are global**, as noted above.

## Updating

Update through the Marketplace/HACS, or replace `themes/modern.yaml` and run
`frontend.reload_themes`. Then hard-refresh the browser — Home Assistant caches the
theme CSS.

## Screenshots

Rendered previews of every variant in light and dark mode go in
[`screenshots/`](screenshots). Until they are added, the tables above are the reference.

## Credits

- [Metrology for Hass](https://github.com/Madelena/Metrology-for-Hass) by Madelena Mak —
  inspiration and palette starting point.
- Microsoft Fluent and Metro design languages — the visual language the palette comes
  from.
- The Home Assistant frontend team — for exposing a real design-token system
  (`--ha-*`, `--wa-*`) that makes a theme like this possible without patches.

## License

[MIT](LICENSE) © 2026 Ricardas
